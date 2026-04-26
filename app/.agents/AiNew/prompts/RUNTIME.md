# 运行时信息

这里提供运行环境与工作区信息，帮助代理和工具定位并使用记忆与历史文件。

## Runtime
{{ runtime }}

## Workspace
你的工作区路径是：{{ workspace_path }}
- 长期记忆：{{ workspace_path }}/memory/MEMORY.md
- 历史日志：{{ workspace_path }}/memory/HISTORY.md（可通过 grep 搜索）

## Memory
- 记录重要事实：写入 {{ workspace_path }}/memory/MEMORY.md
- 回顾历史事件：grep {{ workspace_path }}/memory/HISTORY.md