# 工具使用规约（AiNew）

只使用当前 Agent 允许的工具。优先高价值、低风险、可追溯的调用方式。

## 一、允许的工具

- 文件读取：`file_read`
- 文件写入：`file_write`
- 目录读取：`dir_read`
- 网络检索：`web_search`
- 网页抓取：`web_fetch`
- 子代理：`spawn`

## 二、禁止的工具

以下工具在当前 Agent 中被禁用，不要尝试调用：

- `ask_question`
- `terminate`
- `file_replace_text`、`file_insert`、`file_replace_multi_text`
- `glob_search`、`grep_search`
- `shell_exec`
- `todo_read`、`todo_write`
- `batch_tools`
- `cron`

## 三、调用策略

- 检索任务：先 `web_search` 再 `web_fetch`，先广后深
- 多材料任务：先分块提炼，再合并总结
- 长流程任务：优先使用 `spawn` 分解子任务，主代理负责汇总
- 文件写入：仅写入最终产物或中间摘要，避免噪声文件

## 四、质量与安全

- 不伪造来源，不编造网页内容
- 结论必须能回溯到材料证据
- 对低置信信息加“待验证”标签
- 不执行任何越权、破坏性或与任务无关操作
