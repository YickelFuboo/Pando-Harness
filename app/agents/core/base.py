import json
import logging
import re
from abc import ABC
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from app.config.settings import settings
from app.agents.contants import AGENT_CONFIG_DIR, AGENT_META_FILE, AGENT_USABLE_SKILLS_FILE
from app.agents.sessions.manager import SESSION_MANAGER
from app.agents.sessions.message import Role, Message, ToolCall, Function
from app.infrastructure.llms.chat_models.schemes import ToolArgsParser


def extract_stream_tool_calls(text: str) -> Tuple[str, List[ToolCall]]:
    """从 ask_tools_stream 输出文本中提取 <tool_calls> 块并还原为 ToolCall 列表。"""
    if not text:
        return "", []

    m = re.search(r"<tool_calls>[\s\S]*?</tool_calls>", text)
    if not m:
        return text, []

    tool_block = m.group(0)
    content = (text[:m.start()] + text[m.end():]).strip()
    tool_calls: List[ToolCall] = []

    for jm in re.finditer(r"<tool>\s*([\s\S]*?)\s*</tool>", tool_block):
        payload = jm.group(1).strip()
        try:
            obj = json.loads(payload)
        except Exception:
            continue
        name = obj.get("name") or ""
        if not name:
            continue
        args = obj.get("args")
        if isinstance(args, str):
            parsed = ToolArgsParser.parse(args)
            if ToolArgsParser.ARGS_ERROR_KEY in parsed:
                args = {}
            else:
                args = parsed
        elif not isinstance(args, dict):
            args = {}
        tool_calls.append(
            ToolCall(
                id=obj.get("id") or "",
                function=Function(name=name, arguments=args),
            )
        )
    return content, tool_calls

class AgentState(str, Enum):
    """Agent state enumeration"""
    IDLE = "IDLE"  # Idle state
    RUNNING = "RUNNING"  # Running state
    WAITING = "WAITING"  # Waiting for user input
    ERROR = "ERROR"  # Error state
    FINISHED = "FINISHED"  # Finished state

class ToolChoice(str, Enum):
    """工具调用模式：none=不暴露工具，auto=由模型决定，required=必须调用工具。"""
    NONE = "none"
    AUTO = "auto"
    REQUIRED = "required"

class AgentRunContext(ABC):
    """Agent运行动态上下文"""
    def __init__(
        self,
        agent_type: str,
        channel_type: str,
        channel_id: str,
        session_id: str,
        user_id: str,
        project_path: Optional[str] = None,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        **kwargs: Any,
    ):
        # 客户端信息
        self.channel_type = channel_type
        self.channel_id = channel_id

        # 会话与用户
        self.session_id = session_id
        self.user_id = user_id

        # 模型信息
        self.llm_provider = llm_provider or ""
        self.llm_model = llm_model or ""

        self.params = dict(kwargs)

        # Agent运行空间
        self.workspace_path = self._get_workspace_path() # Agent工作的目标项目路径
        self.project_path = project_path or None  # Agent运行的项目路径

    def _get_workspace_path(self) -> Path:
        return Path(settings.runtime_data_dir) / ".workspace" / self.user_id


class BaseAgent(ABC):
    """Base Agent class

    Base class for all agents, defining basic properties and methods.
    执行类，不参与 schema 序列化，仅用 __init__ 内 self 赋值。
    """

    def __init__(self, agent_type: str):
        # 基本信息
        self.agent_type = agent_type
        self.agent_path = AGENT_CONFIG_DIR / self.agent_type # Agent的定义路径
        self.description: str = ""
        self._load_meta()

        # 提示词信息
        self.system_prompt = "You are pando, a helpful assistant."
        self.user_prompt = ""
        self.next_step_prompt = "Please continue your work."

        # 模型信息
        self.temperature = 0.7
        self.memory_window = 100

        # 执行步数相关
        self._state = AgentState.IDLE
        self._current_step = 0
        self._max_steps = 50
        self._max_duplicate_steps = 2   # 最大重复次数，用于检验当前项agent是否挂死
        self._stop_requested = False

        # 技能相关
        self.skill_names: list[str] = []
        self.skills_extend_enabled = False
        self._load_skills_config()
        

    def _load_meta(self) -> None:
        """Load .agent/{agent_type}/meta.json and set description (English)."""
        meta_path = Path(self.agent_path) / AGENT_META_FILE
        if not meta_path.is_file():
            return
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.description = (data.get("description_en") or "").strip()
        except Exception as e:
            logging.warning("Failed to load meta.json for agent %s: %s", self.agent_type, e)

    def _load_skills_config(self) -> None:
        """从 usable_skills.json 加载 enable_extend（yes/no）与 allow 名单（与 usable_tools 策略一致）。"""
        skills_path = Path(self.agent_path) / AGENT_USABLE_SKILLS_FILE
        if not skills_path.is_file():
            return
        try:
            with open(skills_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logging.warning("Failed to load usable skills config %s: %s", skills_path, e)
            return
        # 解析允许的skills
        skills_policy = data.get("skills")
        if isinstance(skills_policy, dict):
            self.skill_names = [
                str(name)
                for name, decision in skills_policy.items()
                if str(decision).strip().lower() == "allow"
            ]
        # 解析是否允许自扩展skills
        ext = str(data.get("enable_extend", "no")).strip().lower()
        self.skills_extend_enabled = ext == "yes"

    def force_stop(self) -> None:
        """强制当前运行中的 Agent 停止（由外部如 /stop 命令调用）。"""
        self._stop_requested = True

    def reset(self):
        """重置 agent 状态到初始状态
        
        重置以下内容：
        - 状态设置为 IDLE
        - 当前步数归零
        """
        try:
            self._state = AgentState.IDLE
            self._current_step = 0
            self._stop_requested = False
        except Exception as e:
            logging.error(f"Error in agent reset: {str(e)}")
            raise e

    async def run(self, question: str) -> str:
        """Run the agent
        
        Args:
            question: Input question
            
        Returns:
            str: Execution result
        """
        pass
 
    def handle_stuck_state(self):
        """Handle stuck state by adding a prompt to change strategy"""
        stuck_prompt = "\
        Observed duplicate responses. Consider new strategies and avoid repeating ineffective paths already attempted."
        self.next_step_prompt = f"{stuck_prompt}\n{self.next_step_prompt}"
        logging.warning(f"Agent detected stuck state. Added prompt: {stuck_prompt}")

    async def is_stuck(self) -> bool:
        """Check if the agent is stuck in a loop by detecting duplicate content"""
        history = await self.get_history_messages()
        if len(history) < 2:
            return False

        last_message = history[-1]
        if not last_message.content:
            return False

        # Count identical content occurrences
        duplicate_count = sum(
            1
            for msg in reversed(history[:-1])
            if msg.role == Role.ASSISTANT and msg.content == last_message.content
        )

        return duplicate_count >= self._max_duplicate_steps

    def get_state(self) -> AgentState:
        """Get current state
        
        Returns:
            AgentState: Current state
        """
        return self._state
    
    def _strip_think(self, text: str | None) -> str | None:
        """去掉回复中的 <think>...</think> 块（部分思考模型会内嵌），避免把思考过程当正文返回。"""
        if not text:
            return None
        return re.sub(r"<think>[\s\S]*?</think>", "", text).strip() or None

    async def get_history_messages(self) -> List[Message]:
        """Get messages from session"""
        return await SESSION_MANAGER.get_messages(self.session_id)

    async def get_history_context(self) -> List[Dict[str, Any]]:
        """Get history for context"""
        return await SESSION_MANAGER.get_context(self.session_id)

    async def push_history_message(self, message: Message):
        """Add message to session and push user"""
        # 记录会话历史
        await SESSION_MANAGER.add_message(self.session_id, message)

    async def notify_user(self, message: Message):
        """Notify user"""
        msg_dict = message.to_user_message()
        from app.agents.bus.queues import MESSAGE_GATEWAY, OutboundMessage
        await MESSAGE_GATEWAY.push_outbound(OutboundMessage(
            channel_type=self.channel_type,
            channel_id=self.channel_id,
            user_id=self.user_id,
            session_id=self.session_id,
            content=msg_dict.get("content", ""),
        ))

    async def push_history_message_and_notify_user(self, message: Message):
        """Add message to session and push user"""
        await self.push_history_message(message)
        #if message.tool_call_id is None: # 显示工具调用结果消息不通知用户
        await self.notify_user(message)

