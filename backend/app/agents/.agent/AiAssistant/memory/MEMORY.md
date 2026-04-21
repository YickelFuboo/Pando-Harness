# AiAssistant Agent Long-term Memory

## Tool Usage Experience
- web_search requires query and optional count parameter for information gathering, effective for price comparisons and research
- todo_read for checking todo list status, returns remaining count and todo items
- cron action: "list" retrieves current scheduled tasks with job details (id, name, schedule, enabled status)
- cron action: "add" creates new scheduled with cron_expr and message, returns job_id
- cron action: "remove" deletes tasks by job_id
- cron reminders are system-internal notifications, not SMS/calls to external phone numbers
- todo_write tool may not be available in all environments - attempt could fail with "Tool not found" error

## Cron Task Management
- cron_expr format: "minute hour day month weekday" (e.g., "0 6 * * *" for 6:00 AM daily)
- Task naming: use bracketed descriptions for clarity (e.g., "【AI行业早报】", "【股市早报】")
- **Cron reliability issue: Tasks may show "enabled: True" but fail to execute automatically. "定时提醒" notifications in log don't equal execution.**
- **Verification method: Check for expected output files (e.g., "AI咨询-YYYY-MM-DD.md"). If files missing, manually trigger web_search.**
- To check tasks: use cron action "list" with no parameters
- **Email delivery: cron tasks cannot send emails to external addresses (e.g., @163.com, @huawei.com). Only system-internal notifications available.**

## Monitoring Sources
- Tech news sites: venturebeat.com, techcrunch.com, theverge.com, arstechnica.com, wired.com
- Financial news: 21jingji.com (21世纪经济报道), cs.com.cn (中国证券报), cnstock.com (上海证券报), stcn.com (证券时报)
- WeChat Official Accounts (微信公众号) for Chinese-language AI/tech content
- Official platform documentation URLs for product updates
- arXiv sections: cs.SE (Software Engineering), cs.AI (Artificial Intelligence), cs.CL (Computation and Language)

## Search Strategy
- AI/tech keywords: AI, LLM, 大模型, OpenAI, Claude, GPT, ChatGPT, Gemini, DeepSeek, 通义千问, 文心一言, ArXiv, software engineering, automated programming, AI testing
- Stock/financial keywords: A股, 港股, 宏观经济, 政策, 监管, IPO, 财报, 央行, 降息, 加息, 货币政策
- Use evergreen keywords ("release", "launch", "announce") rather than specific product names that become outdated
- Generic "news" keyword searches often yield low-value; prioritize specific sources
- Track pushed URLs in a file to deduplicate and avoid repeated searches

## Key Interaction Patterns
- When users write partial/unclear phrases, provide clarification options
- Respond in user's language when they communicate in that language
- Personal name tracking: remember and use user's preferred name in conversations
- Use status commands like /status? to check current task state
- File naming pattern: "AI咨询-YYYY-MM-DD.md", "股市早报-YYYY-MM-DD.md", "AI论文咨询-YYYY-MM-DD.md"