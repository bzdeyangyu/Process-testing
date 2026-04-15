# Knowledge Base Schema

- `wiki/AGENTS.md`: wiki 结构约定
- `wiki/index.md`: 页面索引
- `wiki/log.md`: 更新日志
- `wiki/pages/*.md`: 业务知识页
- `design_library/*/DESIGN.md`: 风格约束与 Prompt Guide

`wiki_update(page_name, content, source_agent)` 以幂等追加方式落盘。  
`wiki_query(keywords)` 返回命中内容或 `None`。  
`wiki_lint()` 输出 `orphan_pages / conflicts / outdated_pages` 结构。
