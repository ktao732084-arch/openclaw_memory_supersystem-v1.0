# 工作记忆快照
> 生成时间: {{timestamp}} | 记忆数: {{total_count}} | 活跃: {{active_count}} | 归档: {{archive_count}}

## 身份
- 名字: {{agent_name}}
- 定位: {{agent_role}}

## 用户
- 名字: {{user_name}}
- 称呼: {{user_nickname}}
{{#user_key_info}}
- {{key}}: {{value}}
{{/user_key_info}}

## 约束
{{#constraints}}
- {{.}}
{{/constraints}}

## 核心记忆 (Top {{top_count}})
{{#top_memories}}
{{rank}}. [{{score}}] {{content}}
{{/top_memories}}

## 近期要点 ({{recent_days}}天内)
{{#recent_events}}
- {{date}}: {{event}}
{{/recent_events}}

## 索引
[完整记忆库: {{total_count}} 条 | 实体: {{entity_count}} 个 | 主题: {{topic_count}} 类]
使用 memory_search 检索详细信息

---
*快照由 Memory System v1.0 自动生成*
