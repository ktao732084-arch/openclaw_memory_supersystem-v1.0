# Memory System v1.0 设计文档

## 概述

Memory System 是一个基于认知科学原理设计的 AI Agent 记忆系统，实现三层记忆架构、自动整合、智能衰减等功能。

## 设计原则

1. **检索优先** — 不是"记得多"，而是"找得准"
2. **写复杂读简单** — 复杂逻辑在写入时处理，读取 O(1)
3. **重要性由语义决定** — 不依赖使用频率
4. **自动衰减** — 旧记忆自动降权

## 三层架构

### Layer 1: 工作记忆
- 格式: Markdown (snapshot.md)
- 大小: ~2000 tokens
- 更新: 每日 Consolidation 后
- 用途: 每次对话自动注入

### Layer 2: 长期记忆
- 格式: JSONL + JSON
- 分类: facts / beliefs / summaries
- 分池: active（活跃）/ archive（归档）
- 索引: keywords / timeline / relations

### Layer 3: 原始日志
- 来源: OpenClaw Session Transcript
- 用途: Consolidation 时读取
- 原则: 只读不写

## Consolidation 流程

### Phase 1: 轻量全量
- 读取今日对话
- 按规则切分语义片段
- 成本: 0 tokens

### Phase 2: 重要性筛选
- 模型判断重要性
- 标注 importance
- 成本: ~700 tokens

### Phase 3: 深度提取
- 提取 facts/beliefs
- 识别实体
- 成本: ~500 tokens

### Phase 4: Layer 2 维护
- 4a: Facts 去重合并
- 4b: Beliefs 验证
- 4c: Summaries 生成
- 4d: Entities 更新
- 成本: ~400 tokens

### Phase 5: 权重更新
- 应用衰减率
- 归档低分记忆
- 成本: 0 tokens

### Phase 6: 索引更新
- 增量更新索引
- 成本: 0 tokens

### Phase 7: Layer 1 快照
- 生成工作记忆快照
- 成本: ~200 tokens

**总成本: ~1800 tokens/天**

## 重要性评分

### 内在重要性
| 类型 | 分数 |
|------|------|
| 身份/健康/安全 | 1.0 |
| 偏好/关系/状态 | 0.8 |
| 一般事实 | 0.5 |
| 临时信息 | 0.2 |

### 外在信号
| 信号 | 调整 |
|------|------|
| "记住" | +0.5 |
| "重要" | +0.3 |
| "顺便" | -0.2 |

## 衰减机制

### 衰减率
| 类型 | 日衰减 | 半衰期 |
|------|--------|--------|
| Fact | 0.8% | ~87天 |
| Belief | 7% | ~10天 |
| Summary | 2.5% | ~28天 |

### Importance 影响
```
actual_decay = base_decay × (1 - importance × 0.5)
```

## 文件结构

```
memory/
├── config.json
├── layer1/
│   └── snapshot.md
├── layer2/
│   ├── active/
│   │   ├── facts.jsonl
│   │   ├── beliefs.jsonl
│   │   └── summaries.jsonl
│   ├── archive/
│   ├── entities/
│   └── index/
└── state/
    ├── consolidation.json
    └── rankings.json
```

## 与 OpenClaw 集成

1. systemPromptFiles 注入 Layer 1
2. Cron 定时执行 Consolidation
3. AGENTS.md 定义检索规则

## 参考

- Ebbinghaus 遗忘曲线
- 认知科学记忆整合理论
- 现有 AI Agent 记忆系统
