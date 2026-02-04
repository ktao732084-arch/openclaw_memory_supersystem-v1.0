# Consolidation 详解：7 Phase 工作原理

## 整体流程

```
触发条件：冷淡期（20分钟无消息 + 非活跃时段）

Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5 ──→ Phase 6 ──→ Phase 7
 收集        筛选        提取        分类        衰减        索引        快照
 (代码)    (规则+LLM)   (模板+LLM)   (代码)      (代码)      (代码)    (代码+LLM)
```

---

## Phase 1: 收集（Collect）

**处理方式**：100% 代码

**做什么**：从 Layer 3 收集原始对话数据

**输入**：今日的对话日志（`YYYY-MM-DD.md` / `YYYY-MM-DD.jsonl`）

**输出**：切分好的语义片段列表

**机制**：
```python
def collect_segments(date):
    log_path = f"layer3/{date}.jsonl"
    segments = []
    for line in read_jsonl(log_path):
        # 按对话轮次切分
        segment = {
            "content": line["content"],
            "timestamp": line["timestamp"],
            "role": line["role"],
            "context": get_context(line)
        }
        segments.append(segment)
    return segments
```

**Token 消耗**：0

**类比**：睡前回忆今天发生了什么事，先把事情一件件列出来

---

## Phase 2: 筛选（Filter）

**处理方式**：规则优先 + LLM 兜底

**做什么**：判断哪些片段值得记住

**输入**：Phase 1 的片段列表

**输出**：标记为"重要"或"可丢弃"的片段

### 规则过滤（零 Token）

```python
def rule_filter(content):
    # 直接丢弃
    if len(content) < 10:
        return False
    if content in ["好的", "嗯", "OK"]:
        return False
    if is_greeting(content):
        return False
    
    # 直接保留
    if "记住" in content or "重要" in content:
        return True
    if contains_time_reference(content):
        return True
    
    # 无法判断
    return None  # 交给 LLM
```

### LLM 兜底

只有规则无法判断时才调用 LLM：

```
输入: "今天天气真好"
输出: { "keep": false, "reason": "闲聊，无长期价值" }

输入: "我下周三有个重要考试"
输出: { "keep": true, "reason": "时间敏感事件" }
```

**Token 消耗**：~700（取决于需要 LLM 判断的数量）

**类比**：大脑在睡眠时"筛选"哪些经历值得固化成长期记忆

---

## Phase 3: 提取（Extract）

**处理方式**：模板匹配 + LLM 提取

**做什么**：从重要片段中提取结构化信息

**输入**：Phase 2 筛选后的重要片段

**输出**：结构化的 Fact / Belief / Summary 对象

### 模板匹配（零 Token）

```python
PATTERNS = {
    r"我是(.+)": ("fact", "identity"),
    r"我叫(.+)": ("fact", "name"),
    r"我喜欢(.+)": ("fact", "preference"),
    r"(明天|下周.?)(.+)": ("fact", "schedule"),
}

def template_extract(content):
    for pattern, (type, category) in PATTERNS.items():
        match = re.search(pattern, content)
        if match:
            return {
                "type": type,
                "category": category,
                "value": match.group(1),
                "confidence": 0.9
            }
    return None  # 交给 LLM
```

### LLM 提取

复杂情况才调用：

```
输入: "我下周三有个病理学考试，有点紧张"

输出:
- Fact: "用户下周三有病理学考试" (confidence: 0.95)
- Belief: "用户可能对考试感到焦虑" (confidence: 0.7)
- Entities: ["病理学", "考试"]
- Time: "下周三"
```

**Token 消耗**：~500

**类比**：把模糊的记忆"编码"成可存储的格式

---

## Phase 4: 分类（Classify）

**处理方式**：100% 代码（4a/4d）+ LLM（4b/4c）

### Phase 4a: Fact 处理

**做什么**：处理新提取的 Fact

**机制**：
```python
def process_facts(new_facts, existing_facts):
    for new in new_facts:
        # 去重检查
        duplicate = find_duplicate(new, existing_facts)
        if duplicate:
            # 合并：更新时间戳，保留更高置信度
            merge_facts(duplicate, new)
        else:
            # 新增
            existing_facts.append(new)
    return existing_facts
```

**Token 消耗**：0

### Phase 4b: Belief 验证

**做什么**：验证和更新现有 Belief 的置信度

**机制**：
```python
def verify_belief(belief, new_facts):
    # 代码匹配
    for fact in new_facts:
        if belief.content in fact.content:
            belief.confidence += 0.1
            return belief
        if contradicts(belief, fact):
            belief.confidence -= 0.2
            return belief
    
    # 无法判断 → LLM 验证
    return llm_verify(belief, new_facts)
```

**升级/删除规则**：
- 置信度 > 0.85 → 考虑升级为 Fact
- 置信度 < 0.2 → 标记待删除

**Token 消耗**：~200（仅复杂情况）

### Phase 4c: Summary 生成

**做什么**：生成/更新摘要

**机制**：
```python
def generate_summary(facts, threshold=3):
    # 按主题分组
    groups = group_by_topic(facts)
    
    for topic, topic_facts in groups.items():
        if len(topic_facts) >= threshold:
            # 调用 LLM 生成摘要
            summary = llm_summarize(topic_facts)
            save_summary(summary)
```

**Token 消耗**：~200（仅需要生成时）

### Phase 4d: Entities 更新

**做什么**：更新实体档案

**机制**：代码处理，提取并关联实体

**Token 消耗**：0

---

## Phase 5: 衰减（Decay）

**处理方式**：100% 代码

**做什么**：更新所有记忆的权重分数

**机制**：
```python
import math

def apply_decay(records, config):
    decay_rates = config['decay_rates']
    archive_threshold = config['thresholds']['archive']
    
    to_archive = []
    remaining = []
    
    for r in records:
        # 计算衰减
        days = days_since(r['updated'])
        base_rate = decay_rates[r['type']]
        importance = r.get('importance', 0.5)
        
        # 重要性保护：高重要性衰减更慢
        actual_rate = base_rate * (1 - importance * 0.5)
        
        # 应用衰减
        r['score'] = r['score'] * math.exp(-actual_rate * days)
        
        # 归档判断
        if r['score'] < archive_threshold:
            to_archive.append(r)
        else:
            remaining.append(r)
    
    return remaining, to_archive
```

**衰减率配置**：
| 类型 | λ | 半衰期 |
|------|---|--------|
| Fact | 0.008 | ~87天 |
| Belief | 0.07 | ~10天 |
| Summary | 0.025 | ~28天 |

**Token 消耗**：0

**类比**：艾宾浩斯遗忘曲线，不重要的记忆自然淡忘

---

## Phase 6: 索引（Index）

**处理方式**：100% 代码

**做什么**：重建检索索引

**机制**：
```python
def rebuild_indexes(records):
    keywords_index = {}
    relations_index = {}
    timeline_index = {}
    
    for r in records:
        # 关键词索引
        words = segment(r['content'])
        for word in words:
            keywords_index.setdefault(word, []).append(r['id'])
        
        # 实体关系索引
        for entity in r.get('entities', []):
            relations_index.setdefault(entity, []).append(r['id'])
        
        # 时间线索引
        date = r['created'][:10]
        timeline_index.setdefault(date, []).append(r['id'])
    
    return keywords_index, relations_index, timeline_index
```

**输出文件**：
- `index/keywords.json`
- `index/relations.json`
- `index/timeline.json`

**Token 消耗**：0

**类比**：给记忆建立"目录"，方便快速查找

---

## Phase 7: 快照（Snapshot）

**处理方式**：代码生成框架 + 可选 LLM 润色

**做什么**：生成 Layer 1 工作记忆快照

**机制**：
```python
def generate_snapshot(records, config):
    # 按 score 排序
    ranked = sorted(records, key=lambda x: x['score'], reverse=True)
    
    # Token 预算分配
    budget = config['token_budget']['layer1_total']  # 2000
    
    snapshot = f"""# 工作记忆快照
> 生成时间: {now()} | 活跃记忆: {len(records)}

## 🔴 关键信息 (importance ≥ 0.9)
{format_critical(ranked)}

## 📊 记忆排名 (Top 15)
{format_rankings(ranked[:15])}

## 🏷️ 实体索引
{format_entities(ranked)}
"""
    
    return snapshot
```

**Token 消耗**：~200（如需 LLM 润色）

**类比**：每天早上醒来，大脑自动"加载"最重要的记忆到工作区

---

## 总结

| Phase | 功能 | 处理方式 | Token |
|-------|------|---------|-------|
| 1 收集 | 获取原始数据 | 代码 | 0 |
| 2 筛选 | 判断价值 | 规则 + LLM | ~700 |
| 3 提取 | 结构化编码 | 模板 + LLM | ~500 |
| 4 分类 | 归档整理 | 代码 + LLM | ~400 |
| 5 衰减 | 遗忘机制 | 代码 | 0 |
| 6 索引 | 建立关联 | 代码 | 0 |
| 7 快照 | 工作记忆 | 代码 + LLM | ~200 |
| **总计** | | | **~1800** |

**核心原则**：规则优先，LLM 兜底。能用代码解决的不用 LLM。
