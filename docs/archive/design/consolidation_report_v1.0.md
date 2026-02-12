# Consolidation 流程设计报告 v1.0

## 文档信息
- **版本**: 1.0
- **创建时间**: 2026-02-04
- **状态**: 设计完成，待实施
- **关联文档**: `memory_system_design_v1.0.md`

---

## 一、设计理念

### 1.1 Consolidation 的本质

Consolidation 不是"整理记忆"，而是：

**优化检索效率的预处理**

目标：让未来的检索更快、更准、更省 Token。

### 1.2 从检索倒推设计

| 检索问题 | 原因 | Consolidation 应该做什么 |
|---------|------|------------------------|
| 找不到 | 信息没被提取 | **全量提取**，不遗漏 |
| 找到太多 | 冗余信息多 | **去重合并** |
| 找到但不相关 | 语义索引不准 | **优化索引** |
| 找到但太长 | 原始信息啰嗦 | **压缩精炼** |
| 重要的排在后面 | 权重不准 | **重要性标注** |

### 1.3 核心任务

```
1. 全量提取 - 不漏
2. 重要性标注 - 不埋没
3. 去重合并 - 不冗余
4. 压缩精炼 - 不啰嗦
5. 索引优化 - 好检索
```

---

## 二、重要性评分机制

### 2.1 设计原则

**重要性由语义决定，不依赖使用频率。**

原因：用户说一次"我对花生过敏"可能永远不会再提第二次，但这条信息极其重要。

### 2.2 重要性来源

#### 内在重要性（信息本身的性质）

| 类型 | 重要性 | 例子 | intrinsic_score |
|------|--------|------|-----------------|
| 身份属性 | 极高 | 名字、职业、年龄 | 1.0 |
| 健康安全 | 极高 | 过敏、疾病、禁忌 | 1.0 |
| 核心偏好 | 高 | "我讨厌..."、"我喜欢..." | 0.8 |
| 关系信息 | 高 | 家人、朋友、同事 | 0.8 |
| 状态变更 | 高 | 换工作、搬家、分手 | 0.8 |
| 一般事实 | 中 | 日常信息 | 0.5 |
| 临时信息 | 低 | 今天的计划、临时任务 | 0.2 |

#### 外在重要性（用户的表达方式）

| 信号 | explicit_signal |
|------|-----------------|
| "记住"、"以后都" | +0.5 |
| "重要"、"关键" | +0.3 |
| 重复提及 | +0.2 |
| 情绪强烈 | +0.1 |
| "顺便说一下" | -0.2 |

### 2.3 评分公式

```python
importance = intrinsic_score(类型) + explicit_signal(表达) + repetition_bonus(重复)
```

**示例**：
- "我对花生过敏" → 类型=健康安全(1.0) + 无信号(0) = **1.0**
- "记住，我讨厌香菜" → 类型=偏好(0.8) + "记住"(0.5) = **1.3** (cap at 1.0)
- "今天下午开会" → 类型=临时(0.2) + 无信号(0) = **0.2**

---

## 三、分层提取策略

### 3.1 策略选择

**分层提取**（性价比最高）

| 策略 | 成本 | 风险 |
|------|------|------|
| 全量深度提取 | ~3000 tokens | 低 |
| 先判断后提取 | ~1200 tokens | 中（可能漏提取） |
| **分层提取** | ~1200 tokens | **低**（原文保留在 Layer 3） |

### 3.2 分层逻辑

```
Phase 1: 轻量全量（规则，零成本）
  - 保留所有原文，不丢信息
  
Phase 2: 重要性筛选（模型，一次调用）
  - 决定哪些值得深度提取
  
Phase 3: 深度提取（模型，选择性）
  - 只处理重要的内容
```

**优势**：
- Phase 1 全量保留，即使 Phase 2 判断失误，原文还在 Layer 3 可补救
- 成本与"先判断后提取"相同，但风险更低

---

## 四、分池管理机制

### 4.1 问题背景

随着时间累积，Layer 2 记录会越来越多。如果每天都遍历全部记录更新权重，成本会线性增长。

### 4.2 解决方案

将 Layer 2 分成两个池：

| 池 | 内容 | 参与权重重算 |
|---|------|-------------|
| **active/** | score ≥ 0.05 | ✅ 每日重算 |
| **archive/** | score < 0.05 | ❌ 不重算 |

### 4.3 归档与激活规则

| 操作 | 条件 | 动作 |
|------|------|------|
| 归档 | score < 0.05 | active/ → archive/ |
| 激活 | 检索命中归档内容 | archive/ → active/，score = 0.3 |

### 4.4 成本控制效果

| 时间 | 活跃池大小 | 归档池大小 | 重算成本 |
|------|-----------|-----------|---------|
| 第1个月 | ~100 | 0 | O(100) |
| 第6个月 | ~150 | ~200 | O(150) |
| 第1年 | ~200 | ~600 | O(200) |

活跃池趋于**动态平衡**，不会无限增长。

### 4.5 文件结构

```
layer2/
├── active/              # 活跃池
│   ├── facts.jsonl
│   ├── beliefs.jsonl
│   └── summaries.jsonl
├── archive/             # 归档池
│   ├── facts.jsonl
│   ├── beliefs.jsonl
│   └── summaries.jsonl
├── entities/
└── index/
```

---

## 五、完整流程

### 5.1 触发时机

- **主触发**: 冷淡期（每日一次）
- **兜底触发**: 超过 48 小时未执行 或 Layer 3 未处理事件 > 100 条

### 5.2 七阶段流程概览

```
Phase 1: 轻量全量（规则）     → 切分片段
Phase 2: 重要性筛选（模型）   → 决定提取范围
Phase 3: 深度提取（模型）     → 生成 facts/beliefs
Phase 4: Layer 2 维护（混合） → 去重/验证/摘要/实体
Phase 5: 权重更新（规则）     → 衰减 + 归档
Phase 6: 索引更新（规则）     → 增量更新索引
Phase 7: Layer 1 快照（模型） → 生成快照
```

---

## 六、各 Phase 详细实现

### Phase 1: 轻量全量（切分规则）

#### 目标
把 Layer 3 的原始对话切分成**可独立评估的片段**，为 Phase 2 筛选做准备。

#### 切分粒度
不是按消息切，而是按**语义单元**切。

一条消息可能包含多个语义单元：
```
用户: "我叫张三，在北京工作，明天要开会"
      ↓
片段1: "我叫张三"（身份）
片段2: "在北京工作"（状态）
片段3: "明天要开会"（临时）
```

#### 切分规则

```
规则1: 按标点切分
  - 句号、问号、感叹号 → 切分点
  - 逗号、顿号 → 可能的切分点（看长度）

规则2: 按连接词切分
  - "另外"、"还有"、"对了" → 切分点
  - "但是"、"不过"、"然而" → 切分点

规则3: 按主题切分
  - 主语变化 → 切分点
  - 时间词变化（"今天"→"明天"）→ 切分点

规则4: 长度限制
  - 单片段 > 100字 → 强制切分
  - 单片段 < 10字 → 考虑合并
```

#### 基础分类

切分后给每个片段打标签：

| 类型 | 识别规则 | 例子 |
|------|---------|------|
| 陈述 | 无疑问词，陈述句式 | "我在北京" |
| 问题 | 疑问词，问号 | "你能帮我吗？" |
| 指令 | 祈使句，动词开头 | "帮我查一下" |
| 闲聊 | 语气词，无实质内容 | "哈哈"、"好的" |

#### 输出格式

```json
{
  "fragments": [
    {"id": 1, "text": "我叫张三", "type": "陈述", "source": "2026-02-04.jsonl:15"},
    {"id": 2, "text": "在北京工作", "type": "陈述", "source": "2026-02-04.jsonl:15"},
    {"id": 3, "text": "明天要开会", "type": "陈述", "source": "2026-02-04.jsonl:15"},
    {"id": 4, "text": "能帮我订个会议室吗", "type": "指令", "source": "2026-02-04.jsonl:16"}
  ]
}
```

---

### Phase 2: 重要性筛选（Prompt 设计）

#### 目标
一次模型调用，判断哪些片段值得深度提取。

#### Prompt 设计

```
你是一个记忆筛选器。以下是今日对话的片段列表，请判断哪些值得长期记忆。

## 片段列表
{{fragments}}

## 判断标准（按重要性排序）
1. 身份/健康/安全信息 → 必须记忆（importance: 1.0）
2. 明确偏好/关系/状态变更 → 应该记忆（importance: 0.8）
3. 一般事实 → 可选记忆（importance: 0.5）
4. 临时信息/闲聊/指令 → 不记忆（importance: 0）

## 额外信号
- 用户说"记住"、"以后都" → importance +0.5
- 用户说"重要"、"关键" → importance +0.3
- 用户说"顺便"、"随便" → importance -0.2

## 输出格式（JSON）
{
  "selected": [
    {"id": 1, "importance": 1.0, "reason": "身份信息"},
    {"id": 2, "importance": 0.8, "reason": "状态信息"}
  ],
  "skipped": [3, 4]
}

只输出 JSON，不要解释。
```

#### Token 估算
- 输入：片段列表 ~300 tokens + Prompt ~200 tokens = ~500 tokens
- 输出：~200 tokens
- **总计：~700 tokens**

---

### Phase 3: 深度提取（Prompt 设计）

#### 目标
把筛选出的片段转换成结构化的 facts/beliefs。

#### Prompt 设计

```
你是一个信息提取器。请将以下片段转换为结构化记忆。

## 待提取片段
{{selected_fragments}}

## 提取规则
1. 每个片段提取为一条 fact 或 belief
2. fact = 用户明确陈述的事实
3. belief = 需要推断的信息（标注 confidence）
4. 保持简洁，删除冗余词汇
5. 识别涉及的实体（人名、地名、组织等）

## 输出格式（JSON）
{
  "facts": [
    {
      "id": "f_20260204_001",
      "content": "用户名字是张三",
      "importance": 1.0,
      "entities": ["张三"],
      "source": "2026-02-04.jsonl:15"
    }
  ],
  "beliefs": [
    {
      "id": "b_20260204_001",
      "content": "用户可能在科技公司工作",
      "confidence": 0.6,
      "basis": "提到在北京工作，明天开会",
      "source": "2026-02-04.jsonl:15-16"
    }
  ]
}

只输出 JSON，不要解释。
```

#### Token 估算
- 输入：片段 ~200 tokens + Prompt ~200 tokens = ~400 tokens
- 输出：~100 tokens
- **总计：~500 tokens**

---

### Phase 4: Layer 2 维护

#### 4a. Facts 去重合并

**触发条件**：新 fact 与已有 fact 涉及同一实体的同一属性

**判断逻辑**（规则优先）：

```
1. 提取新 fact 的实体和属性
   "用户在上海工作" → 实体=用户, 属性=工作地点, 值=上海

2. 在 active/facts.jsonl 中查找
   是否存在: 实体=用户, 属性=工作地点

3. 如果存在冲突：
   旧 fact: "用户在北京工作"
   新 fact: "用户在上海工作"
   
   → 合并为:
   {
     "id": "f_xxx",
     "content": "用户在上海工作",
     "importance": 0.8,
     "history": [
       {"content": "用户在北京工作", "until": "2026-02-04", "score": 0.3}
     ]
   }
```

**属性识别规则**：

| 属性类型 | 关键词 |
|---------|--------|
| 位置 | 在、住、搬到、去 |
| 职业 | 是、做、当、工作 |
| 状态 | 有、没有、开始、结束 |
| 关系 | 和、跟、认识、分手 |
| 偏好 | 喜欢、讨厌、爱、恨 |

#### 4b. Beliefs 验证

**触发条件**：新 fact 的实体/主题与某个 belief 相关

**逻辑**：

```
遍历 active/beliefs.jsonl:
  如果 belief.entities ∩ new_fact.entities 非空:
    调用模型判断:
      - 证实 → belief 升级为 fact，confidence=1.0
      - 否定 → belief.confidence -= 0.3，若 <0.2 则删除
      - 无关 → 跳过
```

**Prompt**（仅在触发时调用）：

```
已有推断：{{belief.content}}（置信度：{{belief.confidence}}）
新事实：{{new_fact.content}}

请判断新事实对已有推断的影响：
- "confirm" = 证实了推断
- "deny" = 否定了推断
- "irrelevant" = 无关

只输出一个词。
```

#### 4c. Summaries 生成

**触发条件**：同主题 facts ≥ 3 且无对应 summary

**主题聚类规则**：

```
1. 按实体聚类
   所有涉及"张三"的 facts → 一组

2. 按属性聚类
   所有关于"偏好"的 facts → 一组

3. 检查是否已有 summary
   如果 entities/_index.json 中该实体已有 summary → 跳过
   如果没有 → 生成
```

**Prompt**：

```
请将以下相关事实合并为一条摘要：

{{facts_list}}

要求：
- 保留所有关键信息
- 简洁，不超过50字
- 输出格式：{"summary": "..."}
```

#### 4d. Entities 更新

**纯规则，无模型调用**：

```
对每个新 fact:
  提取 entities 列表
  对每个 entity:
    如果 entities/{entity}.json 不存在:
      创建新档案
    否则:
      更新属性
    更新 entities/_index.json
```

**实体档案格式**：

```json
{
  "id": "entity_zhangsan",
  "name": "张三",
  "type": "person",
  "attributes": {
    "location": {"value": "上海", "updated": "2026-02-04"},
    "job": {"value": "工程师", "updated": "2026-01-15"}
  },
  "related_facts": ["f_001", "f_015", "f_023"],
  "related_summaries": ["s_003"]
}
```

---

### Phase 5: 权重更新 + 归档

**纯规则，无模型调用**

#### 5a. 权重更新

```python
for record in active_pool:
    if record.id in today_accessed:
        record.score += ACCESS_BONUS  # 0.1
    else:
        decay = get_decay_rate(record.type, record.importance)
        record.score *= (1 - decay)
```

**衰减率调整**（importance 影响）：

| 类型 | 基础衰减 | importance=1.0 | importance=0.5 |
|------|---------|----------------|----------------|
| fact | 0.008 | 0.004 | 0.008 |
| belief | 0.07 | 0.035 | 0.07 |
| summary | 0.025 | 0.0125 | 0.025 |

公式：`actual_decay = base_decay × (1 - importance × 0.5)`

#### 5b. 归档检查

```python
for record in active_pool:
    if record.score < 0.05:
        move_to_archive(record)
```

#### 5c. 激活处理

```python
pending = read("state/pending_activate.json")
for item in pending.items:
    record = read_from_archive(item.type, item.id)
    record.score = 0.3
    move_to_active(record)
clear("state/pending_activate.json")
```

---

### Phase 6: 索引增量更新

**纯规则，无模型调用**

```python
changes = get_today_changes()  # 新增、修改、归档的记录

for change in changes:
    if change.action == "add":
        add_to_index(change.record)
    elif change.action == "update":
        update_index(change.record)
    elif change.action == "archive":
        remove_from_index(change.record)
```

**索引结构**：

```json
// keywords.json
{
  "北京": ["f_001", "f_023"],
  "工作": ["f_001", "f_015"],
  "过敏": ["f_008"]
}

// timeline.json
{
  "2026-02": ["f_015", "f_016", "f_017"],
  "2026-01": ["f_001", "f_002", "f_008"]
}

// relations.json
{
  "张三": {
    "facts": ["f_001", "f_015"],
    "beliefs": ["b_003"],
    "summaries": ["s_001"]
  }
}
```

---

### Phase 7: Layer 1 快照

#### 触发条件

```python
old_ranking = read("state/rankings.json")
new_ranking = compute_ranking(active_pool)

if ranking_changed(old_ranking, new_ranking, threshold=0.1):
    generate_snapshot()
else:
    skip()  # 复用昨天的
```

#### 快照生成 Prompt

```
根据以下排名生成 Layer 1 快照：

## 排名数据
{{top_20_records}}

## Token 预算分配
- 总预算：2000 tokens
- #1: 40% (800 tokens)
- #2: 25% (500 tokens)
- #3: 15% (300 tokens)
- 其余: 20% (400 tokens)

## 输出格式
按 MEMORY.md 的结构生成 Markdown，包含：
1. Identity（固定）
2. Owner（固定）
3. Constraints（固定）
4. Top Summaries（按预算）
5. Ranked Index（按预算）
6. Recent（最近3天要点）
```

---

## 七、成本汇总

| Phase | 类型 | 成本 | 触发条件 |
|-------|------|------|---------|
| 1 | 规则 | 0 | 每次 |
| 2 | 模型 | ~700 | 每次 |
| 3 | 模型 | ~500 | 每次 |
| 4a | 规则+模型 | ~100 | 有冲突时 |
| 4b | 模型 | ~100 | 有相关时 |
| 4c | 模型 | ~200 | ≥3 facts 时 |
| 4d | 规则 | 0 | 每次 |
| 5 | 规则 | 0 | 每次 |
| 6 | 规则 | 0 | 每次 |
| 7 | 模型 | ~200 | 排名变化时 |

**平均每日成本：~1800 tokens**

---

## 八、失败处理机制

### 8.1 状态记录

在 `state/consolidation.json` 中记录执行状态：

```json
{
  "last_run": "2026-02-04T03:00:00Z",
  "last_success": "2026-02-04T03:00:00Z",
  "current_phase": null,
  "phase_data": {},
  "retry_count": 0
}
```

### 8.2 断点续传

如果执行中断：
1. 记录当前 Phase 和中间数据
2. 下次触发时从断点继续
3. 超过 3 次重试失败 → 告警，等待人工介入

### 8.3 回滚机制

- 每个 Phase 完成后才写入最终结果
- 中途失败不会产生半成品数据
- Layer 3 原始数据始终保留，可重新处理

---

## 九、激活逻辑（Router 侧）

### 9.1 检索时的激活触发

```
Router 检索时：
  1. 先搜 active/
  2. 如果结果不足 → 搜 archive/
  3. 命中 archive/ 内容 → 写入 pending_activate.json
  
Consolidation 时：
  - Phase 5c 处理 pending_activate.json
  - 移回 active/，score = 0.3
```

### 9.2 pending_activate.json 格式

```json
{
  "items": [
    {"type": "fact", "id": "xxx", "triggered_at": "2026-02-04T10:00:00Z"},
    {"type": "belief", "id": "yyy", "triggered_at": "2026-02-04T11:00:00Z"}
  ]
}
```

---

## 十、待优化项（后期实施）

| 问题 | 优化方案 | 优先级 | 状态 |
|------|---------|--------|------|
| Phase 2+3 两次调用 | 合并为一次调用 | 低 | 待评估 |
| Phase 4b 空转 | 已优化：条件触发 | 中 | ✅ 已纳入设计 |
| Phase 6 全量重建 | 已优化：增量更新 | 中 | ✅ 已纳入设计 |
| Phase 7 每天生成 | 已优化：条件生成 | 中 | ✅ 已纳入设计 |
| 冷淡期不可靠 | 已优化：兜底触发 | 高 | ✅ 已纳入设计 |
| 失败处理 | 已优化：断点续传 | 高 | ✅ 已纳入设计 |

---

## 十一、关键设计决策汇总

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 提取策略 | 分层提取 | 性价比最高，风险最低 |
| 重要性判断 | 语义判断（内在+外在） | 不依赖使用频率，不漏重要信息 |
| 去重策略 | 同实体同属性合并 | 保留历史，不丢信息 |
| Beliefs 维护 | 条件触发验证 | 避免空转 |
| Summaries 生成 | 条件触发（≥3 facts） | 按需生成，不浪费 |
| 权重重算范围 | 仅活跃池 | 避免成本线性增长 |
| 索引更新 | 增量更新 | 减少 IO 成本 |
| 快照生成 | 条件生成 | 无变化时跳过 |
| 触发时机 | 冷淡期 + 兜底 | 保证可靠性 |
| 失败处理 | 断点续传 | 保证鲁棒性 |

---

## 十二、与其他模块的接口

### 12.1 与 Router 的接口

- Router 检索 archive/ 时 → 写入 pending_activate.json
- Consolidation Phase 5c → 处理激活

### 12.2 与 Layer 1 的接口

- Consolidation Phase 7 → 生成 snapshot.md
- 每次对话开始 → 读取 snapshot.md

### 12.3 与 Layer 3 的接口

- 实时写入 → Layer 3 事件日志
- Consolidation Phase 1 → 读取今日事件

---

*报告完成。下一步：实际部署方案（与 OpenClaw 集成）*
