import os
import sys
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from app.utils.common import get_project_meta, normalize_path


# 定义全局配置常量
_meta = get_project_meta()
APP_NAME = _meta["name"]
APP_VERSION = _meta["version"]
APP_DESCRIPTION = _meta["description"]

PROJECT_BASE_DIR = Path(__file__).resolve().parents[2]

def is_frozen_runtime() -> bool:
    return bool(getattr(sys, "frozen", False))

def get_runtime_base_dir() -> Path:
    if is_frozen_runtime():
        return Path(sys.executable).resolve().parent
    return PROJECT_BASE_DIR

def get_runtime_config_dir() -> Path:
    if is_frozen_runtime():
        return get_runtime_base_dir() / "config"
    return PROJECT_BASE_DIR / "app" / "config"

def get_runtime_env_file() -> Path:
    if is_frozen_runtime():
        return get_runtime_config_dir() / "env"
    return PROJECT_BASE_DIR / "env.development"

def get_runtime_data_dir() -> Path:
    if is_frozen_runtime():
        return get_runtime_base_dir() / "data"
    return PROJECT_BASE_DIR / "data"


class Settings(BaseSettings):
    """应用配置类 - 平铺结构"""
    
    # 应用基础配置
    service_host: str = Field(default="0.0.0.0", description="服务主机地址", env="SERVICE_HOST")
    service_port: int = Field(default=8000, description="服务端口", env="SERVICE_PORT")
    debug: bool = Field(default=False, description="调试模式", env="DEBUG")
    app_log_level: str = Field(default="INFO", description="日志级别", env="APP_LOG_LEVEL")

    # 认证配置
    auth_user_service_url: str = Field(default="http://localhost:8000", description="User-Service地址", env="AUTH_USER_SERVICE_URL")
    auth_request_timeout: int = Field(default=5, description="请求超时时间(秒)", env="AUTH_REQUEST_TIMEOUT")
    auth_jwks_endpoint: str = Field(default="/.well-known/jwks.json", description="JWKS端点", env="AUTH_JWKS_ENDPOINT")
    auth_jwt_config_endpoint: str = Field(default="/jwt-config", description="JWT配置端点", env="AUTH_JWT_CONFIG_ENDPOINT")
    auth_blacklist_endpoint: str = Field(default="/blacklist", description="黑名单端点", env="AUTH_BLACKLIST_ENDPOINT")
    
    # 数据库配置
    db_name: str = Field(default="knowledge_service", description="数据库名称", env="DB_NAME")
    database_type: str = Field(default="postgresql", description="数据库类型: postgresql/mysql/sqlite", env="DATABASE_TYPE")
    db_pool_size: int = Field(default=10, description="连接池大小", env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, description="最大溢出连接数", env="DB_MAX_OVERFLOW")
    
    # PostgreSQL 配置
    postgresql_host: str = Field(default="localhost", description="PostgreSQL主机地址", env="POSTGRESQL_HOST")
    postgresql_port: int = Field(default=5432, description="PostgreSQL端口", env="POSTGRESQL_PORT")
    postgresql_user: str = Field(default="postgres", description="PostgreSQL用户名", env="POSTGRESQL_USER")
    postgresql_password: str = Field(default="your_password", description="PostgreSQL密码", env="POSTGRESQL_PASSWORD")
    
    # MySQL 配置
    mysql_host: str = Field(default="localhost", description="MySQL主机地址", env="MYSQL_HOST")
    mysql_port: int = Field(default=3306, description="MySQL端口", env="MYSQL_PORT")
    mysql_user: str = Field(default="root", description="MySQL用户名", env="MYSQL_USER")
    mysql_password: str = Field(default="your_password", description="MySQL密码", env="MYSQL_PASSWORD")

    # SQLite 配置
    sqlite_path: Optional[str] = Field(default=None, description="SQLite数据库文件路径(可选)，如 ./data/user.db 或 C:/data/user.db", env="SQLITE_PATH")
    
    # =============================================================================
    # 模型配置说明 见：app/config/xxx.json
    # =============================================================================

    # =============================================================================
    # Web搜索配置 - Web Search
    # =============================================================================
    # Tavily搜索API配置
    tavily_api_key: str = Field(default="", description="Tavily搜索API密钥", env="TAVILY_API_KEY")
    brave_api_key: str = Field(default="", description="Brave搜索API密钥", env="BRAVE_API_KEY")

    # =============================================================================
    # Cron 配置 - 定时任务调度
    # =============================================================================
    run_cron: bool = Field(default=True, description="当前进程是否运行 cron 调度循环；多进程部署时仅在一个进程设为 True，避免重复执行", env="RUN_CRON")

    # =============================================================================
    # Agent配置 - Agent 会话存储
    # =============================================================================
    agent_session_use_local_storage: bool = Field(default=False, description="为 True 时会话存本地文件，为 False 时存数据库", env="AGENT_SESSION_USE_LOCAL_STORAGE")
   
    # =============================================================================
    # 会话压缩 - Session Compaction
    # =============================================================================
    compaction_auto: bool = Field(default=True, description="上下文溢出时是否自动压缩会话", env="COMPACTION_AUTO")
    compaction_reserved: int = Field(default=20_000, description="为压缩预留的 token 缓冲", env="COMPACTION_RESERVED")
    compaction_context_limit: int = Field(default=128_000, description="模型上下文上限(token)，用于溢出判断", env="COMPACTION_CONTEXT_LIMIT")
    compaction_keep_last_n: int = Field(default=6, description="触发压缩时保留的最近消息条数", env="COMPACTION_KEEP_LAST_N")
    compaction_prune: bool = Field(default=True, description="是否启用旧工具输出修剪(prune)", env="COMPACTION_PRUNE")
    compaction_prune_protect: int = Field(default=40_000, description="保护最近工具输出token窗口(prune)", env="COMPACTION_PRUNE_PROTECT")
    compaction_prune_minimum: int = Field(default=20_000, description="触发修剪的最小待修剪token量(prune)", env="COMPACTION_PRUNE_MINIMUM")
    compaction_prune_protected_tools: str = Field(default="skill", description="不参与修剪的工具名(逗号分隔)", env="COMPACTION_PRUNE_PROTECTED_TOOLS")

    class Config:
        env_file = str(get_runtime_env_file())
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    @property
    def database_url(self) -> str:
        """生成数据库连接URL"""
        if self.database_type.lower() == "postgresql":
            return f"postgresql+asyncpg://{self.postgresql_user}:{self.postgresql_password}@{self.postgresql_host}:{self.postgresql_port}/{self.db_name}"
        elif self.database_type.lower() == "mysql":
            return f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.db_name}"
        else:
            raw_path = self.sqlite_path
            if not raw_path:
                filename = self.db_name if self.db_name.lower().endswith(".db") else f"{self.db_name}.db"
                raw_path = str(get_runtime_data_dir() / "sqlite" / filename)
            abs_path = os.path.abspath(raw_path)
            parent_dir = os.path.dirname(abs_path)
            if parent_dir and not os.path.isdir(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
            norm_path = normalize_path(abs_path)
            return f"sqlite+aiosqlite:///{norm_path}"
    
    @property
    def app_name(self) -> str:
        """应用名称(用于JWT issuer等)"""
        return APP_NAME


# 全局配置实例
settings = Settings() 