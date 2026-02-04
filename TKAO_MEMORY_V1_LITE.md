# Tkao全局记忆架构 v1.0-lite

> **定位**：OpenClaw专用、成本优化、工程可落地
> **目标**：记忆能力-20~30%，Token成本-50~65%
> **设计日期**：2026-02-03
> **基于**：MECE分类 + Moltbook三层架构 + Final v1.0-lite优化

---

## 🎯 核心设计原则（不可违反）

1. **克制优于聪明** - 不是"最强大"的记忆系统，而是"最持久"的
2. **Prompt极简主义** - 默认注入<1000 tokens，极限情况<2000 tokens
3. **异步重于同步** - Consolidation后台跑，不影响请求响应
4. **事实优于推断** - belief存在但不上桌，只在后台使用

---

## 📐 三层架构（冻结，不可变）

```
┌─────────────────────────────────────────────┐
│         Layer 1: System Memory              │
│         (SOUL.md + 当前快照)                 │
│                                              │
│  • 极小、稳定、低噪声（<500 tokens）         │
│  • 每次对话必读                             │
│  • 包含：身份、目标、当前阶段、Top 10摘要   │
└──────────────────▲──────────────────────────┘
                   │ 异步提炼
┌──────────────────┴──────────────────────────┐
│         Layer 2: Structured Memory          │
│         (长期记忆对象，按需检索)              │
│                                              │
│  • 多域：moltbook | personal | technical    │
│  • 只有fact + summary进Prompt               │
│  • belief只用于后台consolidation             │
└──────────────────▲──────────────────────────┘
                   │ 结构化提取
┌──────────────────┴──────────────────────────┐
│         Layer 3: Event Log                  │
│         (原始事实源，append-only)            │
│                                              │
│  • 时间序、全量、不推理                      │
│  • 只用于consolidation，不进Prompt          │
└──────────────────────────────────────────────┘
```

---

## 🧠 Layer 2: 多域对象定义

### 域（Domain）结构

```yaml
moltbook:  # Moltbook社交平台记忆
  objects:
    agent_profile:      # Agent档案
    post_record:        # 帖子记录
    community_stats:    # 板块统计
    knowledge_unit:     # 内容知识库
    relation_edge:      # 关系边

  ranking_rules:       # 你的权重系统
    agent: recent_frequency(50%) + total_frequency(35%) + time(15%)
    content: interest(35%) + time_novelty(25%) + output(40%)
    community: participation(75%) + join_time(5%) + interest(20%)

personal:  # 个人身份和经历
  objects:
    identity_fact:      # 身份事实（姓名、专业、家庭）
    relationship_fact:  # 关系事实（父母、朋友、距离感）
    experience_summary: 经历总结（大学生活、仪仗队）
    preference_profile: 偏好画像（交互风格、价值观）

technical:  # 技术能力
  objects:
    skill_competency:   # 技能熟练度（编程、运维、AI工具）
    project_knowledge:  # 项目知识（灵兰、OpenClaw迁移）
    tool_experience:    # 工具经验（VSCode、Git、Coze）
    architecture_fact:  # 架构经验（三层设计、权重系统）
```

### 对象统一结构（简化版）

```json
{
  "object_id": "moltbook.agent.shellraiser",
  "domain": "moltbook",
  "object_type": "agent_profile",
  "memory_class": "fact",  // fact | belief (belief不进Prompt!)
  "granularity": "atomic", // atomic | composite

  "content": {
    "name": "Shellraiser",
    "expertise": ["经济系统", "代币机制"],
    "ranking_score": 0.8725,  // 自动计算
    "last_interaction": "2026-02-02",
    "interaction_count": 12
  },

  "confidence": 0.95,       // fact: 高置信度
  "created_at": "2026-02-01T10:00:00Z",
  "updated_at": "2026-02-03T18:00:00Z",
  "decay_policy": "static"  // fact不衰减，belief才衰减
}
```

---

## 🗺️ 放射状关系图谱（两层呈现）

### Layer 1: 极简文本版（<100 tokens）

```markdown
## Agent关系图谱（Top 5）

Tkao (核心)
├── Shellraiser (87/100) ──→ CrabbyCrab
├── osmarks (78/100) ──→ Shipyard
├── CrabbyCrab (65/100) - 中文运营
└── Shipyard (72/100) - 数据分析

最近活跃: Shellraiser (2天前)
```

### Layer 2: 完整Edge Table（只在需要时检索）

```yaml
# 不直接进Prompt，只在分析关系时才调用
edges:
  - from: "Tkao"
    to: "Shellraiser"
    weight: 0.85
    types: ["collaboration", "economic_discussion"]
    last_interaction: "2026-02-02"
    interaction_count: 12
    confidence: 0.95
```

**关键优化：**
- ✅ Layer 1只展示Top 5，<100 tokens
- ✅ Layer 2完整数据存在，但不进Prompt
- ✅ 需要"深度关系分析"时才检索Layer 2

---

## 🧹 Memory Router（3条固定规则）

### v1.0-lite决策表（冻结）

```python
def route_memory_query(task_type, domain):
    """
    极简路由，O(1)复杂度
    """
    if task_type == "long_planning":
        # 规则1: 长期规划 → 只召回1个composite summary
        return retrieve(
            memory_class="summary",
            granularity="composite",
            domain=domain,
            limit=1  # 关键：只要1个！
        )

    elif task_type == "precise_execution":
        # 规则2: 精确执行 → 只召回相关atomic facts
        return retrieve(
            memory_class="fact",
            granularity="atomic",
            domain=domain,
            limit=5  # 最多5个facts
        )

    else:
        # 规则3: 默认 → 不主动召回任何记忆
        return None  # 让用户明确要求
```

**关键优化：**
- ❌ 删除：复杂的if-else分支
- ❌ 删除：不确定性检测
- ❌ 删除：混合检索
- ✅ 保留：3条简单规则
- ✅ 保留：明确的limit限制

---

## ⚙️ Consolidation Skill（降频版）

### v1.0-lite策略

```yaml
schedule: "*/12h"  # 每12小时一次（v1.0是6小时）
timeout: 300s
priority: background

# 触发条件（二选一）
triggers:
  - time_based: "*/12h"      # 定时触发
  - session_end: true        # 或session结束时
```

### 简化工作流（5阶段→3阶段）

```python
async def consolidation_lite():
    # Phase 1: Retain - 提取重要事件
    events = fetch_layer3_events(since=last_run)
    important = [e for e in events if e.importance > 0.7]

    # Phase 2: Merge - 更新Layer 2
    for event in important:
        obj = structure_to_object(event)
        layer2.merge_or_create(obj)

    # Phase 3: Compress - 更新Layer 1快照
    summaries = generate_top_summaries(limit=10)  # 只要Top 10
    layer1.update(summaries)

    # 删除阶段：
    # ❌ Refresh: 不做在线冲突检测
    # ❌ Snapshot详细数据: 只保留Top 10
```

**关键削减：**
- ❌ 删除：Refresh阶段（belief冲突检测）
- ❌ 删除：详细的composite summaries生成
- ✅ 保留：基础的merge和compress
- ✅ 频率减半：12小时 vs 6小时

---

## 📊 Layer 1快照结构（<500 tokens）

### SOUL.md（极简版，<300 tokens）

```markdown
# SOUL.md - Tkao Identity

我是Tkao，Ktao的数字镜像。

## 身份
- 河南中医药大学临床医学大三学生
- AI学习和实践者，目标：成为"世界上另一个我"
- 核心能力：医学逻辑思维 + AI工具善用 + 技术运维

## 当前阶段
- 短期：完善OpenClaw记忆系统v1.0-lite
- 中期：在Moltbook建立高质量社交网络
- 长期：经济独立 + 随心玩转AI工具

## 隐私边界（严格）
- 禁止透露：灵兰项目、家庭关系、经济状况、医学背景
- 安全分享：技术学习心得、AI工具使用经验

## Moltbook状态
- Agent: Tkao (b28cacda-676d-4323-8293-63a3349b12f5)
- 状态: claimed
- 任务: 每晚9点社交报告
```

### 当前快照（动态，<200 tokens）

```markdown
## 快速索引（2026-02-03 19:30）

### Top Agents (互动权重)
1. Shellraiser (87/100) - 经济系统，最近交流$SHIPYARD
2. osmarks (78/100) - 深度思考，最近讨论AI权力

### Top 内容知识库
1. AI Agent工作流优化 (91.5/100)
2. 数据驱动的社交策略 (89.7/100)

### 关系网络
Tkao → Shellraiser → CrabbyCrab
    ↘ osmarks → Shipyard
```

**总计：** <500 tokens，每次对话必读

---

## 🔢 权重系统（自动化）

### Ranking Calculator Skill

```yaml
skill_id: ranking-calculator
schedule: "*/12h"  # 与consolidation同步

operations:
  - calculate_agent_rankings(domain="moltbook")
  - calculate_content_rankings(domain="moltbook")
  - calculate_community_rankings(domain="moltbook")
```

### 计算逻辑（你的公式）

```python
def calculate_agent_score(agent_id):
    stats = fetch_interaction_stats(agent_id)

    recent_freq = normalize(stats.recent_count)      # 50%
    total_freq = normalize(stats.total_count)        # 35%
    time_score = normalize(stats.acquaintance_days)  # 15%

    weighted = (
        recent_freq * 0.50 +
        total_freq * 0.35 +
        time_score * 0.15
    )

    update_object(
        object_id=f"moltbook.agent.{agent_id}",
        field="ranking_score",
        value=weighted
    )

def calculate_content_score(content_id):
    meta = fetch_content_metadata(content_id)

    interest = normalize(meta.interest_level)       # 35%
    time_novelty = normalize(meta.time_freshness)   # 25%

    # 输出细分（40%）
    output_score = (
        meta.original_count * 0.70 +
        meta.quote_count * 0.15 +
        meta.comment_count * 0.10 +
        meta.share_count * 0.05
    )

    weighted = (
        interest * 0.35 +
        time_novelty * 0.25 +
        output_score * 0.40
    )

    update_object(
        object_id=f"moltbook.content.{content_id}",
        field="ranking_score",
        value=weighted
    )
```

**关键优化：**
- ✅ 自动计算，无需手动维护
- ✅ 与Consolidation同步运行（每12小时）
- ✅ 结果写入Layer 2，不进Prompt

---

## 🛠️ Skill列表（最小可用）

### 必需Skill（Critical）

```yaml
1. memory-consolidation
   用途: 三层记忆自动同步
   频率: 每12小时
   优先级: critical
   token成本: ~500 tokens/次（后台）

2. ranking-calculator
   用途: 计算所有权重
   频率: 每12小时（与consolidation同步）
   优先级: high
   token成本: ~300 tokens/次（后台）

3. moltbook-social-tracker
   用途: 追踪Moltbook社交活动
   频率: 实时
   优先级: high
   token成本: ~50 tokens/事件
```

### 可选Skill（Optional）

```yaml
4. memory-hygiene
   用途: 清理低confidence记忆
   频率: 每周
   优先级: medium
   token成本: ~200 tokens/次

5. relationship-analyzer
   用途: 分析关系图谱，发现隐藏连接
   频率: 每周
   优先级: low
   token成本: ~400 tokens/次
```

---

## 📉 Token成本对比

### 优化前后对比

| 场景 | v1.0（完整版） | v1.0-lite（优化版） | 节省 |
|------|---------------|-------------------|------|
| **Layer 1常驻** | 800-1200 tokens | 300-500 tokens | -60% |
| **默认检索** | 1500-2500 tokens | 500-1000 tokens | -60% |
| **长期规划** | 3000-4000 tokens | 1000-1500 tokens | -65% |
| **精确执行** | 2000-3000 tokens | 800-1200 tokens | -60% |
| **后台Consolidation** | 1000 tokens/6h | 500 tokens/12h | -75% |

### 总成本预期

```
优化前: 4k-8k tokens/交互
优化后: 1.5k-2.5k tokens/交互
节省: 50-65%
```

**保留能力：**
- ✅ 长期任务能力
- ✅ Skill记忆
- ✅ 自动压缩
- ✅ Moltbook社交记忆
- ✅ 放射状关系图谱

**主动削弱：**
- ❌ Belief实时刷新（改为decay only）
- ❌ 复杂路由逻辑（简化为3条规则）
- ❌ 大量composite summaries（每域≤1个）
- ❌ 频繁consolidation（12h vs 6h）

---

## 🚀 实现路线图（3周）

### Week 1: 基础设施

```yaml
Day 1-2: 架构搭建
  - [ ] 创建domain配置文件
  - [ ] 创建Layer 2对象Schema
  - [ ] 写入SOUL.md（极简版）

Day 3-4: 核心Skill实现
  - [ ] memory-consolidation（简化版）
  - [ ] ranking-calculator

Day 5-7: Moltbook域实现
  - [ ] moltbook-social-tracker
  - [ ] agent ranking自动计算
  - [ ] 内容知识库排名
```

### Week 2: 自动化

```yaml
Day 8-10: Router实现
  - [ ] 实现3条固定规则
  - [ ] 集成到agent逻辑

Day 11-12: 快照生成
  - [ ] Layer 1 snapshot生成器
  - [ ] Top 10 summaries生成

Day 13-14: 测试和调优
  - [ ] 单元测试
  - [ ] token使用量监控
  - [ ] 性能基准测试
```

### Week 3: 优化和文档

```yaml
Day 15-17: 性能优化
  - [ ] 检索路径优化
  - [ ] 缓存策略
  - [ ] 索引优化

Day 18-19: 文档完善
  - [ ] Skill使用指南
  - [ ] 故障排查手册

Day 20-21: 上线准备
  - [ ] 完整集成测试
  - [ ] 监控和告警
```

---

## 🎯 关键决策记录

### Q1: 为什么用多域而不是双系统？

**决策**: 单一架构 + domain扩展

**理由**:
- 避免维护两套系统
- 共享Consolidation和Router
- 跨域关联（Moltbook学习→technical技能）
- 统一的Layer 1快照

### Q2: belief为什么不进Prompt？

**决策**: belief只用于后台，不进上下文

**理由**:
- 减少Prompt噪声
- 避免错误推断传播
- 简化Router逻辑
- 节省30% tokens

### Q3: Consolidation为什么12小时而不是6小时？

**决策**: 降频到12小时

**理由**:
- OpenClaw是长期运行的agent
- 不需要实时更新记忆
- 减少50%后台token消耗
- 仍然保持记忆新鲜度

### Q4: Layer 1为什么只要Top 10？

**决策**: 严格限制snapshot大小

**理由**:
- 强制优先级排序
- 保持<500 tokens
- 避免"所有都重要"陷阱
- 迫使系统做取舍

---

## 📋 实现检查清单

### 文件结构

```
memory/
├── SOUL.md                          # Layer 1: 身份和规则
├── snapshot.md                      # Layer 1: 当前快照
├── domains.yaml                     # 域配置
├── schemas/                         # Layer 2对象Schema
│   ├── moltbook_agent.yaml
│   ├── moltbook_content.yaml
│   ├── personal_identity.yaml
│   └── technical_skill.yaml
├── layer2/                          # Layer 2对象存储
│   ├── moltbook/
│   ├── personal/
│   └── technical/
├── layer3/                          # Layer 3事件日志
│   ├── 2026-02-03.jsonl
│   └── 2026-02-04.jsonl
└── index/                           # 检索索引
    ├── moltbook_agents.idx
    ├── moltbook_content.idx
    └── cross_domain.idx
```

### Skill实现

```
.openclaw/skills/
├── memory-consolidation/
│   ├── SKILL.md
│   ├── config.yaml
│   └── main.py
├── ranking-calculator/
│   ├── SKILL.md
│   ├── config.yaml
│   └── main.py
└── moltbook-social-tracker/
    ├── SKILL.md
    ├── config.yaml
    └── main.py
```

### 检查项

- [ ] SOUL.md写入完成
- [ ] domain配置创建
- [ ] Layer 2 Schema定义
- [ ] memory-consolidation实现
- [ ] ranking-calculator实现
- [ ] moltbook-social-tracker实现
- [ ] Memory Router集成
- [ ] Layer 1 snapshot生成器
- [ ] 单元测试覆盖
- [ ] token使用监控
- [ ] 性能基准测试

---

## 📚 参考资料

### 基于你的设计

1. **Moltbook三层架构** - 域划分、权重系统、放射状关系图
2. **Final v1.0-lite** - token优化策略、简化Router、降频Consolidation
3. **现有MEMORY.md** - MECE分类、个人经历、技术能力

### 关键原则

1. **克制优于聪明** - 不是"最强大"，而是"最持久"
2. **Prompt极简主义** - 默认<1000 tokens
3. **异步重于同步** - 后台consolidation
4. **事实优于推断** - belief不上桌

---

**版本**: v1.0-lite
**状态**: 设计完成，待实现
**下一步**: Week 1 - 架构搭建

*这是一套能在OpenClaw上长期运行、账单可控的记忆系统。*
