# Memory System v1.0

三层记忆架构系统，让 AI Agent 拥有真正的长期记忆。

## 特性

- 🧠 **三层记忆架构**：工作记忆 → 长期记忆 → 原始日志
- ⚡ **自动整合**：每日 Consolidation，无需手动维护
- 🎯 **智能衰减**：重要信息永不遗忘，琐碎信息自然淡化
- 📊 **结构化存储**：Facts / Beliefs / Summaries 分类管理
- 🔍 **高效检索**：多维索引，毫秒级响应

## 快速开始

```bash
# 初始化
python3 scripts/memory.py init

# 添加记忆
python3 scripts/memory.py capture "用户对花生过敏" --type fact --importance 1.0

# 执行整合
python3 scripts/memory.py consolidate --force

# 查看状态
python3 scripts/memory.py status
```

## 文档

- [SKILL.md](SKILL.md) - 完整使用文档
- [docs/design.md](docs/design.md) - 设计文档

## 性能

| 指标 | 数值 |
|------|------|
| 单条记忆添加 | ~39ms |
| Consolidation (100条) | ~51ms |
| 存储空间 (100条) | 64KB |
| Layer 1 快照 | ~690 tokens |

## 许可证

MIT License
