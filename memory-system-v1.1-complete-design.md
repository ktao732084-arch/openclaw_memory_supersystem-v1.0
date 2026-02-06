# Memory System v1.1 完整设计方案
## 三级过滤漏斗 + 访问日志 + 时间敏感记忆

**设计日期**: 2026-02-05  
**版本**: v1.0 → v1.1  
**核心理念**: 规则优先，LLM 兜底，脑科学启发

---

## 🧠 设计哲学：借鉴人类记忆机制

### 人类记忆的三个特征
1. **工作记忆容量有限**（7±2 chunks）→ Layer 1 快照 2000 tokens
2. **重复强化记忆**（Hebbian Learning）→ 访问日志加成
3. **遗忘曲线**（Ebbinghaus）→ 衰减机制 + 时间敏感过期

### AI 记忆的独特需求
1. **精确检索**（不像人类会"想不起来"）→ 多维索引
2. **成本敏感**（Token 消耗）→ 三级漏斗，规则优先
3. **上下文依赖**（每次对话重新加载）→ 访问频率决定注入优先级

---

## 📊 核心参数配置

### 1. 三级漏斗触发阈值

```python
FUNNEL_CONFIG = {
    # 第一级：强匹配池（0 Token）
    "tier1_patterns": {
        "permanent": [
            r"我叫|我是|我的名字",
            r"过敏|疾病|健康问题",
            r"喜欢|讨厌|偏好",
            r"家人|父母|兄弟|姐妹"
        ],
        "task_immediate": [
            r"(今天|今晚|现在|马上|立刻).*(做|去|完成|提交)",
            r"\d{1,2}[点时].*(会议|开会|见面)"
        ],
        "task_short": [
            r"(明天|后天|一会儿|待会).*(做|去|完成|提交)"
        ]
    },
    
    # 第二级：LLM 介入阈值（基于 importance 分数）
    "tier2_threshold": {
        "lower": 0.35,  # < 0.35: 直接判定为临时信息
        "upper": 0.70   # > 0.70: 直接判定为重要信息
        # 0.35-0.70: 灰色地带，调用 LLM
    },
    
    # 第三级：实体热度追踪
    "tier3_entity": {
        "default_ttl_days": 3,      # 默认保质期 3 天
        "reactivation_extend": 3,   # 再次提到延长 3 天
        "max_ttl_days": 14          # 最长保质期 14 天
    }
}
```

**设计理由**：
- **0.35-0.70 灰色地带**：参考人类"不确定"的记忆（约 40% 的日常信息）
- **3 天保质期**：人类短期记忆约 2-7 天，取中间值
- **14 天上限**：超过 2 周未激活，说明不重要

---

### 2. 访问日志加成参数

```python
ACCESS_BOOST_CONFIG = {
    "coefficient": 0.2,           # 加成系数
    "max_boost": 0.5,             # 最大加成 50%
    "log_base": "natural",        # 使用自然对数 ln
    "decay_factor": 0.95,         # 访问记录衰减（每天）
    
    # 访问权重（不同访问类型的权重）
    "access_weights": {
        "retrieval": 1.0,         # 检索到但未使用
        "used_in_response": 2.0,  # 用于生成回复
        "user_mentioned": 3.0     # 用户主动提及
    }
}
```

**公式**：
```python
# 基础公式
boost = ln(weighted_count + 1) * (weighted_count / days) * 0.2

# 加权访问次数
weighted_count = sum(access_weight * count for each type)

# 示例：
# - 检索 10 次（权重 1.0）
# - 用于回复 5 次（权重 2.0）
# - 用户提及 2 次（权重 3.0）
# weighted_count = 10*1 + 5*2 + 2*3 = 26
```

**设计理由**：
- **ln 对数**：防止刷分，边际递减（符合 Weber-Fechner 定律）
- **权重区分**：用户主动提及 > 用于回复 > 仅检索（符合强化学习原理）
- **0.2 系数**：保证高频记忆能快速拉满（5 次用于回复 ≈ 0.5 boost）

---

### 3. 时间敏感记忆过期时间

```python
TIME_SENSITIVITY_CONFIG = {
    # 立即任务（当天）
    "immediate": {
        "keywords": ["今天", "今晚", "现在", "马上", "立刻"],
        "expires_hours": 12
    },
    
    # 短期任务（1-3天）
    "short_term": {
        "keywords": ["明天", "后天", "一会儿", "待会"],
        "expires_days": 2
    },
    
    # 中期任务（1-2周）
    "medium_term": {
        "keywords": ["这周", "下周", "最近"],
        "expires_days": 10
    },
    
    # 长期任务（1个月）
    "long_term": {
        "keywords": ["这个月", "下个月"],
        "expires_days": 35
    },
    
    # 具体时间点（会议、约会）
    "specific_time": {
        "pattern": r"\d{1,2}[点时]",
        "action_keywords": ["会议", "开会", "见面", "约", "到"],
        "expires_after_hours": 2  # 事件后 2 小时过期
    }
}
```

**设计理由**：
- **12 小时**：当天任务，睡前过期
- **2 天**："明天"的任务，后天就过期
- **10 天**："这周"的任务，下周中期过期
- **35 天**："这个月"的任务，下月初过期
- **事件后 2 小时**：会议结束后短暂保留，用于回顾

---

### 4. 衰减与访问的关系

```python
DECAY_WITH_ACCESS_CONFIG = {
    # 基础衰减率（v1.0 保持不变）
    "base_decay": {
        "fact": 0.008,
        "belief": 0.07,
        "summary": 0.025
    },
    
    # 访问保护期（最近访问过的记忆衰减慢）
    "access_protection": {
        "within_3_days": 0.99,    # 3 天内访问：几乎不衰减
        "within_7_days": 0.97,    # 7 天内访问：轻微衰减
        "within_14_days": 0.95,   # 14 天内访问：正常衰减
        "beyond_14_days": 1.0     # 超过 14 天：按基础衰减率
    }
}
```

**设计理由**：
- **3 天保护期**：对应人类"工作记忆"持续时间
- **7 天缓冲期**：对应人类"短期记忆"转化期
- **14 天正常期**：超过 2 周未用，说明不常用

---

## 🔄 完整工作流程

### Phase 0: 清理过期记忆（新增）

```python
def phase0_expire_memories():
    """清理过期记忆"""
    now = datetime.now()
    
    for pool in ['active', 'archive']:
        for mem_type in ['facts', 'beliefs', 'summaries']:
            memories = load_memories(pool, mem_type)
            valid = []
            expired = []
            
            for mem in memories:
                expires_at = mem.get('expires_at')
                
                if expires_at and datetime.fromisoformat(expires_at) <= now:
                    expired.append(mem)
                else:
                    valid.append(mem)
            
            # 保存有效记忆
            save_memories(pool, mem_type, valid)
            
            # 归档过期记忆（不删除）
            if expired:
                archive_expired_memories(expired)
                print(f"✓ 归档 {len(expired)} 条过期记忆")
```

---

### Phase 1: 提取 + 三级漏斗（更新）

```python
def phase1_extract_with_funnel(transcript):
    """Phase 1: 提取 + 三级漏斗"""
    segments = split_transcript(transcript)
    memories = []
    
    for seg in segments:
        # ===== 第一级：强匹配池 =====
        tier1_result = check_tier1_patterns(seg)
        if tier1_result:
            memory = create_memory_from_tier1(seg, tier1_result)
            memories.append(memory)
            continue
        
        # ===== 计算 importance =====
        importance = calculate_importance(seg)
        
        # ===== 第二级：LLM 介入 =====
        if 0.35 <= importance <= 0.70:
            llm_result = call_llm_time_sensor(seg, importance)
            memory = create_memory_from_llm(seg, llm_result)
            memories.append(memory)
            continue
        
        # ===== 高于 0.70：直接判定为重要 =====
        if importance > 0.70:
            memory = create_memory_permanent(seg, importance)
            memories.append(memory)
            continue
        
        # ===== 低于 0.35：判定为临时信息 =====
        if importance < 0.35:
            memory = create_memory_temporary(seg, importance)
            memories.append(memory)
            continue
    
    # ===== 第三级：实体热度追踪 =====
    memories = apply_tier3_entity_tracking(memories)
    
    return memories
```

---

### 第一级：强匹配池实现

```python
def check_tier1_patterns(segment):
    """第一级：强匹配池（0 Token）"""
    import re
    
    content = segment['content']
    
    # 检查永久记忆模式
    for pattern in FUNNEL_CONFIG['tier1_patterns']['permanent']:
        if re.search(pattern, content):
            return {
                'type': 'permanent',
                'expires_at': None,
                'confidence': 1.0
            }
    
    # 检查立即任务
    for pattern in FUNNEL_CONFIG['tier1_patterns']['task_immediate']:
        if re.search(pattern, content):
            expires_at = (datetime.now() + timedelta(hours=12)).isoformat()
            return {
                'type': 'task',
                'expires_at': expires_at,
                'confidence': 0.9
            }
    
    # 检查短期任务
    for pattern in FUNNEL_CONFIG['tier1_patterns']['task_short']:
        if re.search(pattern, content):
            expires_at = (datetime.now() + timedelta(days=2)).isoformat()
            return {
                'type': 'task',
                'expires_at': expires_at,
                'confidence': 0.9
            }
    
    # 检查具体时间点
    time_match = re.search(r'(\d{1,2})[点时]', content)
    if time_match:
        for keyword in TIME_SENSITIVITY_CONFIG['specific_time']['action_keywords']:
            if keyword in content:
                hour = int(time_match.group(1))
                meeting_time = datetime.now().replace(hour=hour, minute=0)
                if meeting_time < datetime.now():
                    meeting_time += timedelta(days=1)
                expires_at = (meeting_time + timedelta(hours=2)).isoformat()
                return {
                    'type': 'task',
                    'expires_at': expires_at,
                    'confidence': 0.95
                }
    
    return None
```

---

### 第二级：LLM 时空传感器

```python
def call_llm_time_sensor(segment, importance):
    """第二级：LLM 时空传感器（仅在灰色地带调用）"""
    
    prompt = f"""请评估以下内容的时间敏感性：

内容："{segment['content']}"
初步重要性：{importance}

请回答：
1. 这是持久信息（身份/偏好/关系）还是瞬时信息（任务/行程/琐事）？
2. 如果是瞬时信息，预计多少天后会失去时效性？
3. 最终重要性评分（0-1）

输出 JSON 格式：
{{
  "type": "permanent" 或 "task",
  "expires_in_days": <天数或null>,
  "importance": <0-1分数>,
  "reasoning": "<简短理由>"
}}"""
    
    # 调用 LLM（使用最便宜的模型）
    response = call_llm(prompt, model="cheap")
    result = json.loads(response)
    
    # 计算过期时间
    if result['type'] == 'task' and result['expires_in_days']:
        expires_at = (datetime.now() + timedelta(days=result['expires_in_days'])).isoformat()
    else:
        expires_at = None
    
    return {
        'type': result['type'],
        'expires_at': expires_at,
        'importance': result['importance'],
        'confidence': 0.8,  # LLM 判断的置信度略低
        'reasoning': result['reasoning']
    }
```

---

### 第三级：实体热度追踪

```python
def apply_tier3_entity_tracking(memories):
    """第三级：实体热度追踪"""
    
    # 加载活跃实体池
    active_entities = load_active_entities()
    
    for mem in memories:
        entities = mem.get('entities', [])
        
        # 检查是否提到活跃实体
        mentioned_entities = [e for e in entities if e in active_entities]
        
        if mentioned_entities and not mem.get('expires_at'):
            # 提到了活跃实体，但没有明确的过期时间
            # 判断是否有动作词
            has_action = check_action_verbs(mem['content'])
            
            if not has_action:
                # 没有动作词，归类为"待审核记忆"
                mem['is_permanent'] = False
                mem['expires_at'] = (datetime.now() + timedelta(days=3)).isoformat()
                mem['tier3_tracked'] = True
                mem['reactivation_count'] = 0
    
    return memories

def check_action_verbs(content):
    """检查是否包含动作词"""
    action_verbs = ["做", "去", "完成", "提交", "开会", "见面", "买", "卖", "学", "教"]
    return any(verb in content for verb in action_verbs)
```

---

### Phase 5: 排名（加入访问加成）

```python
def phase5_rank_with_access_boost(memories):
    """Phase 5: 排名（加入访问频率加成）"""
    import math
    
    for mem in memories:
        # 基础分数
        base_score = mem['importance'] * mem['confidence']
        
        # 访问频率加成
        access_count = mem.get('access_count', 0)
        created_at = datetime.fromisoformat(mem['created_at'])
        days_since_creation = (datetime.now() - created_at).days + 1
        
        # 加权访问次数
        weighted_count = calculate_weighted_access_count(mem)
        
        # 计算加成
        if weighted_count > 0:
            boost = math.log(weighted_count + 1) * (weighted_count / days_since_creation) * 0.2
            boost = min(boost, 0.5)  # 限制最大 50%
        else:
            boost = 0
        
        mem['access_boost'] = boost
        mem['final_score'] = base_score * (1 + boost)
    
    # 按最终分数排序
    return sorted(memories, key=lambda x: x['final_score'], reverse=True)

def calculate_weighted_access_count(memory):
    """计算加权访问次数"""
    weights = ACCESS_BOOST_CONFIG['access_weights']
    
    retrieval_count = memory.get('retrieval_count', 0)
    used_count = memory.get('used_in_response_count', 0)
    mentioned_count = memory.get('user_mentioned_count', 0)
    
    weighted = (
        retrieval_count * weights['retrieval'] +
        used_count * weights['used_in_response'] +
        mentioned_count * weights['user_mentioned']
    )
    
    return weighted
```

---

### Phase 6: 衰减（考虑访问时间）

```python
def phase6_decay_with_access_protection(memories):
    """Phase 6: 衰减（考虑最后访问时间）"""
    
    for mem in memories:
        # 获取基础衰减率
        base_decay = DECAY_WITH_ACCESS_CONFIG['base_decay'][mem['type']]
        
        # 检查最后访问时间
        last_accessed = mem.get('last_accessed')
        
        if last_accessed:
            days_since_access = (datetime.now() - datetime.fromisoformat(last_accessed)).days
            
            # 根据访问时间调整衰减率
            if days_since_access <= 3:
                decay_factor = 0.99  # 3 天内：几乎不衰减
            elif days_since_access <= 7:
                decay_factor = 0.97  # 7 天内：轻微衰减
            elif days_since_access <= 14:
                decay_factor = 0.95  # 14 天内：正常衰减
            else:
                decay_factor = 1.0 - base_decay  # 超过 14 天：按基础衰减
        else:
            decay_factor = 1.0 - base_decay
        
        # 应用衰减
        mem['confidence'] *= decay_factor
        
        # 检查是否需要归档
        if mem['confidence'] < 0.05:
            mem['should_archive'] = True
    
    return memories
```

---

### 访问日志记录

```python
def record_access(memory_id, access_type, query=None, context=None):
    """记录访问日志
    
    access_type: 'retrieval' | 'used_in_response' | 'user_mentioned'
    """
    
    # 记录到访问日志文件
    log_entry = {
        "memory_id": memory_id,
        "timestamp": datetime.now().isoformat(),
        "access_type": access_type,
        "query": query,
        "context": context
    }
    
    log_path = get_memory_dir() / 'layer2' / 'access_log.jsonl'
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    # 更新记忆条目的访问统计
    memory = load_memory_by_id(memory_id)
    
    # 更新对应类型的计数
    count_key = f"{access_type}_count"
    memory[count_key] = memory.get(count_key, 0) + 1
    memory['access_count'] = memory.get('access_count', 0) + 1
    memory['last_accessed'] = datetime.now().isoformat()
    
    # 如果是第三级追踪的记忆，检查是否需要延长保质期
    if memory.get('tier3_tracked'):
        memory['reactivation_count'] = memory.get('reactivation_count', 0) + 1
        current_expires = datetime.fromisoformat(memory['expires_at'])
        new_expires = datetime.now() + timedelta(days=3)
        
        # 延长保质期，但不超过 14 天
        max_expires = datetime.now() + timedelta(days=14)
        memory['expires_at'] = min(new_expires, max_expires).isoformat()
    
    # 保存更新
    save_memory(memory)
```

---

## 📝 数据结构更新

### 记忆条目完整结构

```json
{
  "id": "fact_20260205_a3f2e1",
  "type": "fact",
  "content": "Ktao 喜欢轻松互动风格",
  "importance": 0.8,
  "confidence": 0.95,
  "created_at": "2026-02-05T13:00:00Z",
  "last_updated": "2026-02-05T13:00:00Z",
  "entities": ["Ktao"],
  "tags": ["user_preference"],
  
  // ===== 时间敏感 =====
  "expires_at": null,
  "is_permanent": true,
  
  // ===== 访问追踪 =====
  "access_count": 15,
  "retrieval_count": 10,
  "used_in_response_count": 5,
  "user_mentioned_count": 2,
  "last_accessed": "2026-02-05T14:00:00Z",
  "access_boost": 0.35,
  
  // ===== 第三级追踪 =====
  "tier3_tracked": false,
  "reactivation_count": 0,
  
  // ===== 排名 =====
  "final_score": 1.026
}
```

---

## 🎯 配置文件更新

### config.json

```json
{
  "version": "1.1",
  
  "decay_rates": {
    "fact": 0.008,
    "belief": 0.07,
    "summary": 0.025
  },
  
  "thresholds": {
    "archive": 0.05,
    "summary_trigger": 3
  },
  
  "token_budget": {
    "layer1_total": 2000
  },
  
  "consolidation": {
    "fallback_hours": 48
  },
  
  // ===== 新增：三级漏斗 =====
  "funnel": {
    "tier2_threshold_lower": 0.35,
    "tier2_threshold_upper": 0.70,
    "tier3_default_ttl_days": 3,
    "tier3_reactivation_extend_days": 3,
    "tier3_max_ttl_days": 14
  },
  
  // ===== 新增：访问追踪 =====
  "access_tracking": {
    "enabled": true,
    "boost_coefficient": 0.2,
    "max_boost": 0.5,
    "weights": {
      "retrieval": 1.0,
      "used_in_response": 2.0,
      "user_mentioned": 3.0
    },
    "protection_days": {
      "strong": 3,
      "medium": 7,
      "weak": 14
    }
  },
  
  // ===== 新增：时间敏感 =====
  "time_sensitivity": {
    "enabled": true,
    "immediate_hours": 12,
    "short_term_days": 2,
    "medium_term_days": 10,
    "long_term_days": 35,
    "event_after_hours": 2
  }
}
```

---

## 🚀 实施计划

### Phase 1: 时间敏感记忆（2-3天）
- [ ] 实现 Phase 0 过期清理
- [ ] 实现第一级强匹配池
- [ ] 实现第二级 LLM 时空传感器
- [ ] 实现第三级实体热度追踪
- [ ] 更新 Phase 1 提取逻辑
- [ ] 测试过期机制

### Phase 2: 访问日志系统（2-3天）
- [ ] 添加访问日志文件结构
- [ ] 实现 `record_access()` 函数
- [ ] 实现加权访问计数
- [ ] 更新 Phase 5 排名逻辑
- [ ] 更新 Phase 6 衰减逻辑
- [ ] 测试访问追踪

### Phase 3: 整合测试（1-2天）
- [ ] 更新 config.json
- [ ] 迁移现有数据
- [ ] 端到端测试
- [ ] 性能测试
- [ ] 文档更新

---

## 💡 关键设计决策总结

### 1. 为什么 0.35-0.70 是灰色地带？
- **< 0.35**: 明显不重要（"随便说说"）
- **> 0.70**: 明显重要（"我对花生过敏"）
- **0.35-0.70**: 不确定（"机票订好了"）→ 需要 LLM 判断

### 2. 为什么访问权重是 1:2:3？
- **检索到（1.0）**: 只是匹配，未必有用
- **用于回复（2.0）**: 确实有用，强化记忆
- **用户提及（3.0）**: 用户主动强调，最强信号

### 3. 为什么 3 天保质期？
- 人类短期记忆：2-7 天
- AI 对话频率：通常 1-3 天一次
- 平衡点：3 天（既不太短，也不太长）

### 4. 为什么 ln 对数？
- 防止刷分：10 次 → ln(11) = 2.4，100 次 → ln(101) = 4.6
- 边际递减：符合 Weber-Fechner 定律
- 快速拉满：5 次高权重访问 ≈ 0.5 boost

---

**设计完成！准备开始实现。** 🦞
