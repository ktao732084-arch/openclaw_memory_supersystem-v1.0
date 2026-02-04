# 处理策略：规则优先，LLM 兜底

## 核心原则

**能用代码解决的不用 LLM，省 Token。**

LLM 是"重型武器"，调用成本高、延迟大。我们的策略是：
- 简单情况 → 代码/规则处理
- 复杂情况 → LLM 处理
- 模糊情况 → 规则初筛 + LLM 兜底

---

## 各 Phase 处理策略

| Phase | 简单情况（代码） | 复杂情况（LLM） |
|-------|-----------------|----------------|
| Phase 1 收集 | ✅ 代码切分 | ✅ 代码切分 |
| Phase 2 筛选 | ✅ 规则过滤 | 规则 + LLM |
| Phase 3 提取 | ✅ 正则/模板 | LLM 提取 |
| Phase 4a Fact | ✅ 代码去重 | ✅ 代码去重 |
| Phase 4b Belief | ✅ 代码匹配 | LLM 验证 |
| Phase 4c Summary | 跳过 | LLM 生成 |
| Phase 5 衰减 | ✅ 代码计算 | ✅ 代码计算 |
| Phase 6 索引 | ✅ 代码重建 | ✅ 代码重建 |
| Phase 7 快照 | ✅ 代码生成 | 代码 + LLM 润色 |

---

## Phase 2 筛选策略

### 规则优先（零 Token）

```python
def rule_filter(content):
    # 直接丢弃
    if len(content) < 10:
        return False, "太短"
    
    if content.strip() in ["好的", "嗯", "OK", "好", "行", "可以"]:
        return False, "无意义回复"
    
    if is_greeting(content):  # "你好"、"早上好" 等
        return False, "问候语"
    
    if is_pure_emoji(content):
        return False, "纯表情"
    
    # 直接保留
    if "记住" in content or "重要" in content:
        return True, "用户标记重要"
    
    if contains_time_reference(content):  # "明天"、"下周" 等
        return True, "时间敏感"
    
    if contains_personal_info(content):  # "我是"、"我的" 等
        return True, "个人信息"
    
    # 无法判断 → 交给 LLM
    return None, "需要 LLM 判断"
```

### LLM 兜底

只有 `rule_filter` 返回 `None` 时才调用 LLM。

---

## Phase 3 提取策略

### 模板匹配（零 Token）

```python
PATTERNS = {
    # 身份类
    r"我是(.+)": lambda m: {"type": "fact", "category": "identity", "value": m.group(1)},
    r"我叫(.+)": lambda m: {"type": "fact", "category": "name", "value": m.group(1)},
    
    # 偏好类
    r"我喜欢(.+)": lambda m: {"type": "fact", "category": "preference", "value": m.group(1)},
    r"我不喜欢(.+)": lambda m: {"type": "fact", "category": "dislike", "value": m.group(1)},
    
    # 时间类
    r"(明天|后天|下周.?|下个月)(.+)": lambda m: {"type": "fact", "category": "schedule", "time": m.group(1), "event": m.group(2)},
}

def template_extract(content):
    for pattern, extractor in PATTERNS.items():
        match = re.search(pattern, content)
        if match:
            return extractor(match)
    return None  # 交给 LLM
```

### LLM 提取

复杂情况才调用：
- 隐含信息（"最近有点累" → Belief: 用户可能压力大）
- 多重含义
- 需要上下文理解

---

## Phase 4b Belief 验证策略

### 代码匹配（零 Token）

```python
def code_verify_belief(belief, new_facts):
    # 直接证据匹配
    for fact in new_facts:
        if belief.content in fact.content:
            return {"action": "increase", "delta": 0.1}
        if contradicts(belief.content, fact.content):
            return {"action": "decrease", "delta": 0.2}
    
    # 无新证据
    return {"action": "none"}
```

### LLM 验证

只有以下情况才调用：
- 语义相似但不完全匹配
- 需要推理判断是否矛盾
- 置信度处于临界值（0.4-0.6）

---

## Phase 5/6 衰减和索引

**100% 代码处理**，永远不需要 LLM：

```python
# Phase 5: 衰减计算
import math

def apply_decay(record, days, config):
    base_rate = config['decay_rates'][record['type']]
    importance = record.get('importance', 0.5)
    actual_rate = base_rate * (1 - importance * 0.5)
    record['score'] = record['score'] * math.exp(-actual_rate * days)
    return record

# Phase 6: 索引重建
def rebuild_keyword_index(records):
    index = {}
    for r in records:
        words = segment(r['content'])  # 分词
        for word in words:
            if len(word) >= 2:
                index.setdefault(word, []).append(r['id'])
    return index
```

---

## Token 节省效果

| 场景 | 纯 LLM 方案 | 规则优先方案 | 节省 |
|------|------------|-------------|------|
| 10 条记忆 | ~2000 tokens | ~200 tokens | 90% |
| 50 条记忆 | ~8000 tokens | ~500 tokens | 94% |
| 100 条记忆 | ~15000 tokens | ~800 tokens | 95% |

---

## 决策流程图

```
输入片段
    │
    ▼
┌─────────────┐
│ 规则判断    │
└─────────────┘
    │
    ├─── 明确保留 ──→ 保留
    │
    ├─── 明确丢弃 ──→ 丢弃
    │
    └─── 无法判断 ──→ LLM 判断 ──→ 保留/丢弃
```

---

## 配置项

在 `config.json` 中可调整：

```json
{
  "processing": {
    "use_rules_first": true,
    "llm_fallback": true,
    "min_content_length": 10,
    "skip_greetings": true,
    "skip_pure_emoji": true
  }
}
```
