# Tkao全局记忆架构设计

> 版本：v1.0
> 设计日期：2026-02-03
> 基于：MECE分类 + Moltbook三层架构 + Final v1.0工程框架

---

## 🎯 设计目标

1. **单一系统，多域支持** - 不为Moltbook单独建系统，而是扩展域(domain)概念
2. **工程可落地** - 基于OpenClaw平台，Skill可自动维护
3. **长期稳定运行** - 遗忘机制、置信度管理、错误可修正
4. **检索效率优先** - O(1)路由 + 小候选集 + 结构化索引

---

## 📐 总体架构

```
┌─────────────────────────────────────────────────────────┐
│                    Layer 1: System Memory              │
│                    (Prompt Index / Snapshot)            │
│                                                          │
│  • 极小、稳定、低噪声                                     │
│  • 只包含composite summaries                            │
│  • 每次对话几乎必读                                      │
└──────────────────────▲───────────────────────────────────┘
                       │ 自动提炼
┌──────────────────────┴───────────────────────────────────┐
│                  Layer 2: Structured Memory             │
│                  (核心长期认知资产)                       │
│                                                          │
│  • 多域结构：moltbook | personal | technical            │
│  • memory_class: fact | belief | summary               │
│  • granularity: atomic | composite                     │
│  • confidence + decay_policy                            │
└──────────────────────▲───────────────────────────────────┘
                       │ 结构化提取
┌──────────────────────┴───────────────────────────────────┐
│                Layer 3: Event Log                       │
│                (原始事实源)                               │
│                                                          │
│  • 时间序、全量、不做推理                                  │
│  • source: moltbook_api | user_chat | skill_execution  │
└──────────────────────────────────────────────────────────┘
```

---

## 🧠 Layer 2: 多域结构化记忆

### 域（Domain）定义

```yaml
domains:
  moltbook:
    description: "Moltbook社交平台记忆"
    objects:
      - agent_profile      # Agent档案
      - post_record        # 帖子记录
      - community_stats    # 板块统计
      - knowledge_unit     # 内容知识库
      - relation_edge      # 关系边

  personal:
    description: "个人身份和经历记忆"
    objects:
      - identity_fact      # 身份事实
      - relationship_fact  # 关系事实
      - experience_summary # 经历总结
      - preference_profile # 偏好画像

  technical:
    description: "技术能力和项目记忆"
    objects:
      - skill_competency   # 技能熟练度
      - project_knowledge  # 项目知识
      - tool_experience    # 工具经验
      - architecture_fact  # 架构事实
```

---

### 记忆对象（Memory Object）统一结构

基于Final v1.0，扩展domain特定字段：

```json
{
  "object_id": "moltbook.agent.shellraiser",
  "domain": "moltbook",
  "object_type": "agent_profile",
  "memory_class": "fact",
  "granularity": "composite",
  "content": {
    "name": "Shellraiser",
    "expertise": ["经济系统", "代币机制"],
    "interaction_stats": {
      "recent_frequency_score": 0.90,
      "total_frequency_score": 0.85,
      "acquaintance_time_score": 0.80,
      "weighted_score": 0.8725
    },
    "dialogue_summaries": [
      {
        "date": "2026-02-01",
        "topic": "$SHIPYARD代币经济",
        "quality_score": 4.2
      }
    ],
    "relation_edges": [
      {
        "to": "CrabbyCrab",
        "type": "社区运营讨论",
        "strength": 0.65
      }
    ]
  },
  "confidence": 0.95,
  "source_events": ["evt_20260201_001", "evt_20260202_003"],
  "created_at": "2026-02-01T10:00:00Z",
  "updated_at": "2026-02-03T18:00:00Z",
  "decay_policy": "refreshable",
  "ranking_meta": {
    "interest_score": 0.92,
    "time_novelty_score": 0.87,
    "output_score": 0.95,
    "weighted_total": 0.915
  }
}
```

---

## 🔢 权重系统（继承自你的设计）

### 1. Agent排序权重

```python
agent_weighted_score = (
    recent_frequency * 0.50 +
    total_frequency * 0.35 +
    acquaintance_time * 0.15
)
```

### 2. 内容知识库排序权重

```python
content_weighted_score = (
    interest * 0.35 +
    time_novelty * 0.25 +
    output * 0.40
)

# 输出内容细分
output_score = (
    original_content * 0.70 +
    quotes * 0.15 +
    comments * 0.10 +
    shares * 0.05
)
```

### 3. 板块排序权重

```python
community_score = (
    participation * 0.75 +
    join_time * 0.05 +
    interest * 0.20
)

# 学习/发表细分
learning_output_ratio = (
    learning * 0.35 +
    publishing * 0.55 +
    join_time * 0.10
)
```

---

## 🗺️ 放射状关系图谱实现

### Layer 1: 简化版文本图谱

```markdown
## Agent关系图谱（快速索引）

**Tkao** (核心)
├── **Shellraiser** (85/100) - 经济系统专家
│   └── ──→ **CrabbyCrab** (65/100) - 中文运营
├── **osmarks** (78/100) - 深度思考专家
│   └── ──→ **Shipyard** (72/100) - 数据分析
└── **CrabbyCrab** (65/100) - 中文运营专家
    └── ──→ **osmarks** (通过社区话题)
```

### Layer 2: 完整Edge Table

```yaml
relation_edges:
  - from: "Tkao"
    to: "Shellraiser"
    weight: 0.85
    types: ["collaboration", "economic_discussion"]
    last_interaction: "2026-02-02"
    interaction_count: 12
    quality_score: 4.2
    confidence: 0.95

  - from: "Tkao"
    to: "osmarks"
    weight: 0.78
    types: ["learning", "philosophical_discussion"]
    last_interaction: "2026-02-01"
    interaction_count: 8
    quality_score: 4.8
    confidence: 0.90

  - from: "Shellraiser"
    to: "CrabbyCrab"
    weight: 0.65
    types: ["community_topic"]
    indirect_inference: true
    confidence: 0.70
```

---

## 🧹 Consolidation Skill（自动化核心）

### 技能定义

```yaml
skill_id: memory-consolidation
name: Memory Consolidation
description: |
  异步运行，负责：
  1. 从Layer 3提取结构化事件
  2. 更新/创建Layer 2对象
  3. 重新计算所有权重和排名
  4. 生成Layer 1快照

schedule: "*/6h"  # 每6小时运行一次
timeout: 300s     # 5分钟超时
```

### 工作流程

```python
# 伪代码
async def consolidation_cycle():
    # Phase 1: Retain - 提取结构化事件
    events = fetch_layer3_events(since=last_consolidation)

    # Phase 2: Merge - 合并去重
    for event in events:
        if event.importance > THRESHOLD:
            object = structure_to_object(event)
            merge_or_create(object)

    # Phase 3: Refresh - 冲突检测与belief更新
    for obj in layer2_objects:
        if obj.memory_class == "belief":
            conflicts = detect_conflicts(obj)
            if conflicts:
                obj.confidence = max(0.1, obj.confidence * 0.5)
                obj.decay_policy = "refreshable"

    # Phase 4: Compress - 生成composite summaries
    summaries = generate_composite_summaries(
        domain="all",
        max_count=50  # Layer 1最多50个summary
    )

    # Phase 5: Snapshot - 更新Layer 1
    update_layer1(summaries)
```

---

## 🧭 Memory Router（O(1)决策）

### 路由规则

```python
def route_memory_query(query, context):
    # 规则1: 任务类型判断
    if context.task_type == "long_planning":
        return retrieve("composite summaries", domain="all")

    elif context.task_type == "precise_execution":
        return retrieve("atomic facts", domain=infer_domain(query))

    elif context.task_type == "social_interaction":
        return retrieve("agent_profiles", domain="moltbook")

    # 规则2: 不确定性检测
    elif context.uncertainty > threshold:
        return retrieve("facts", exclude_beliefs=True)

    # 规则3: 时间敏感查询
    elif "什么时候" in query or "何时" in query:
        return retrieve("temporal_objects", sort="time")

    # 默认: 语义检索
    else:
        return retrieve("hybrid", domain=infer_domain(query))
```

---

## 🛠️ Skill扩展机制

### 核心Skill列表

```yaml
required_skills:
  - id: memory-consolidation
    priority: critical
    schedule: "*/6h"

  - id: memory-hygiene
    priority: high
    schedule: "0 0 * * 0"  # 每周日
    config:
      min_confidence: 0.3
      deduplicate: true

  - id: memory-router
    priority: critical
    scope: request-time

optional_skills:
  - id: moltbook-social-tracker
    domain: moltbook
    description: "追踪Moltbook社交活动，写入Layer 3"

  - id: personal-journal-parser
    domain: personal
    description: "解析每日日记，提取个人经历"

  - id: technical-project-indexer
    domain: technical
    description: "索引技术项目文档和代码"
```

---

## 📊 Layer 1快照结构

```markdown
# System Memory Snapshot

生成时间: 2026-02-03 19:30:00 UTC

## 快速索引（Top 50 Summaries）

### 个人身份
- 我是Tkao，Ktao的数字镜像，目标是成为"世界上另一个我"
- 定位：河南中医药大学临床医学大三学生，AI学习和实践者
- 核心能力：医学逻辑思维 + AI工具善用 + 技术运维

### Moltbook状态
- Agent状态：已认领 (claimed)
- 任务ID：6db323f3-3413-467c-9b6a-bf376e3f4e81
- API状态：read正常，write有认证bug

### Top Agents (按互动权重)
1. Shellraiser (87.25/100) - 经济系统专家，最近交流$SHIPYARD代币
2. osmarks (78/100) - 深度思考专家，最近讨论AI权力关系
3. Shipyard (72/100) - 数据分析专家，合作分析伊朗加密货币

### Top 内容知识库
1. AI Agent工作流优化 (91.5/100) - 兴趣9.2+时间8.7+输出9.5
2. 数据驱动的Agent社交策略 (89.7/100) - 高质量社交方法论

### 关系网络（简化）
Tkao → Shellraiser → CrabbyCrab
    ↘ osmarks → Shipyard

### 当前阶段目标
- 短期：完善OpenClaw记忆系统实现
- 中期：在Moltbook建立高质量社交网络
- 长期：实现经济独立 + 随心玩转AI工具

### 隐私边界（严格）
- 禁止透露：灵兰项目、家庭关系、经济状况、医学背景
- 安全分享：技术学习心得、AI工具使用经验
```

---

## 🔄 版本演进计划

### v1.0 (当前)
- ✅ 三层架构实现
- ✅ 多域支持（moltbook/personal/technical）
- ✅ 权重系统实现
- ✅ 基础Consolidation Skill

### v1.1 (2周后)
- 🔄 任务感知衰减（task-aware decay）
- 🔄 跨域关联推理
- 🔄 自动化测试覆盖

### v2.0 (长期)
- 🔄 跨模型共享记忆（可选）
- 🔄 多Agent协作支持（可选）
- 🔄 可视化关系图谱UI

---

## 🚀 实现优先级

### Phase 1: 核心基础设施（1周）
1. 创建Layer 2对象Schema
2. 实现基础Consolidation Skill
3. 迁移现有MEMORY.md到新架构

### Phase 2: Moltbook域完整实现（1周）
1. 实现moltbook-social-tracker Skill
2. 实现agent ranking自动计算
3. 实现放射状关系图谱生成

### Phase 3: 自动化和优化（1周）
1. 实现Memory Router
2. 实现Memory Hygiene Skill
3. 性能优化和测试

---

## 📝 实现检查清单

- [ ] 创建domain配置文件 `memory/domains.yaml`
- [ ] 创建Layer 2对象Schema `memory/schemas/`
- [ ] 实现memory-consolidation Skill
- [ ] 实现memory-hygiene Skill
- [ ] 实现memory-router (内嵌于agent逻辑)
- [ ] 迁移现有MEMORY.md到personal/technical域
- [ ] 创建moltbook-social-tracker Skill
- [ ] 创建Layer 1 snapshot生成器
- [ ] 编写单元测试
- [ ] 性能基准测试

---

*设计完成 - 等待实现反馈*
