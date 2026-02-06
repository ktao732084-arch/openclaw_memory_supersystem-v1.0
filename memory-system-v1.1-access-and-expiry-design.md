# Memory System v1.1 设计方案
## 新增功能：访问日志 + 时间敏感记忆

**设计日期**: 2026-02-05  
**版本**: v1.0 → v1.1  
**目标**: 在现有系统基础上，增加访问追踪和记忆过期机制

---

## 🎯 设计目标

### 1. 访问日志（Access Log）
**问题**: v1.0 设计中提到了"访问频率加成"，但未实现  
**目标**: 记录每次记忆被检索/使用的情况，让常用记忆权重更高

### 2. 时间敏感记忆（Time-Sensitive Memory）
**问题**: 临时信息（如"明天3点开会"）会永久保留，造成混乱  
**目标**: 为记忆添加过期时间，自动清理过时信息

---

## 📊 数据结构变更

### 1. 记忆条目新增字段

**现有结构**（v1.0）:
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
  "tags": ["user_preference"]
}
```

**新增字段**（v1.1）:
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
  
  // ===== 新增字段 =====
  "expires_at": null,              // 过期时间（null = 永不过期）
  "access_count": 5,               // 访问次数
  "last_accessed": "2026-02-05T14:00:00Z",  // 最后访问时间
  "access_boost": 0.15             // 访问频率加成（自动计算）
}
```

### 2. 访问日志文件

**新增文件**: `memory/layer2/access_log.jsonl`

```json
{
  "memory_id": "fact_20260205_a3f2e1",
  "timestamp": "2026-02-05T14:00:00Z",
  "query": "Ktao的交互风格是什么？",
  "context": "用户询问交互偏好",
  "retrieval_score": 0.92,
  "used_in_response": true
}
```

**字段说明**:
- `memory_id`: 被访问的记忆ID
- `timestamp`: 访问时间
- `query`: 触发检索的查询（可选）
- `context`: 访问上下文（可选）
- `retrieval_score`: 检索时的匹配分数
- `used_in_response`: 是否被用于生成回复

---

## 🔧 功能实现

### 功能 1: 访问日志追踪

#### 1.1 记录访问

**触发时机**: 每次检索记忆时

```python
def record_access(memory_id, query=None, context=None, score=None, used=True):
    """记录记忆访问"""
    log_entry = {
        "memory_id": memory_id,
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "context": context,
        "retrieval_score": score,
        "used_in_response": used
    }
    
    # 追加到访问日志
    log_path = get_memory_dir() / 'layer2' / 'access_log.jsonl'
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    # 更新记忆条目的访问统计
    update_memory_access_stats(memory_id)
```

#### 1.2 更新访问统计

```python
def update_memory_access_stats(memory_id):
    """更新记忆的访问统计"""
    # 读取记忆条目
    memory = load_memory_by_id(memory_id)
    
    # 更新访问次数和时间
    memory['access_count'] = memory.get('access_count', 0) + 1
    memory['last_accessed'] = datetime.now().isoformat()
    
    # 计算访问频率加成
    memory['access_boost'] = calculate_access_boost(memory)
    
    # 保存更新
    save_memory(memory)
```

#### 1.3 计算访问频率加成

```python
def calculate_access_boost(memory):
    """计算访问频率加成
    
    公式: access_boost = (access_count / days_since_creation) * 0.1
    
    示例:
    - 创建 10 天，访问 20 次 → boost = 0.2
    - 创建 100 天，访问 10 次 → boost = 0.01
    """
    created_at = datetime.fromisoformat(memory['created_at'])
    days_since_creation = (datetime.now() - created_at).days + 1  # 避免除零
    
    access_count = memory.get('access_count', 0)
    
    # 访问频率 = 访问次数 / 天数
    access_frequency = access_count / days_since_creation
    
    # 加成系数 0.1（可配置）
    boost = access_frequency * 0.1
    
    # 限制最大加成为 0.5
    return min(boost, 0.5)
```

#### 1.4 应用访问加成到检索

**在 Phase 5 排名时应用**:

```python
def phase5_rank_with_access_boost(memories):
    """Phase 5: 排名（加入访问频率加成）"""
    for mem in memories:
        # 原有分数
        base_score = mem['importance'] * mem['confidence']
        
        # 访问频率加成
        access_boost = mem.get('access_boost', 0)
        
        # 最终分数 = 基础分数 * (1 + 加成)
        mem['final_score'] = base_score * (1 + access_boost)
    
    # 按最终分数排序
    return sorted(memories, key=lambda x: x['final_score'], reverse=True)
```

---

### 功能 2: 时间敏感记忆

#### 2.1 识别时间敏感内容

**触发时机**: Phase 1 提取时

```python
def detect_time_sensitivity(content):
    """检测内容是否时间敏感
    
    返回: (is_sensitive, expires_at)
    """
    import re
    from datetime import datetime, timedelta
    
    # 时间敏感关键词
    time_patterns = {
        "明天": timedelta(days=1),
        "后天": timedelta(days=2),
        "下周": timedelta(days=7),
        "下个月": timedelta(days=30),
        "今天": timedelta(hours=24),
        "今晚": timedelta(hours=12),
        "一会儿": timedelta(hours=6),
        "待会": timedelta(hours=3)
    }
    
    # 检查是否包含时间敏感词
    for keyword, delta in time_patterns.items():
        if keyword in content:
            expires_at = (datetime.now() + delta).isoformat()
            return True, expires_at
    
    # 检查具体时间（如"3点开会"）
    time_match = re.search(r'(\d{1,2})[点时]', content)
    if time_match and any(word in content for word in ["会议", "开会", "见面", "约"]):
        hour = int(time_match.group(1))
        now = datetime.now()
        meeting_time = now.replace(hour=hour, minute=0, second=0)
        
        # 如果时间已过，设为明天
        if meeting_time < now:
            meeting_time += timedelta(days=1)
        
        # 会议后2小时过期
        expires_at = (meeting_time + timedelta(hours=2)).isoformat()
        return True, expires_at
    
    # 不是时间敏感内容
    return False, None
```

#### 2.2 创建时间敏感记忆

```python
def create_memory_with_expiry(content, type, importance, expires_at=None):
    """创建记忆（支持过期时间）"""
    memory = {
        "id": generate_id(type, content),
        "type": type,
        "content": content,
        "importance": importance,
        "confidence": 1.0,
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "expires_at": expires_at,  # 新增
        "access_count": 0,         # 新增
        "last_accessed": None,     # 新增
        "access_boost": 0.0        # 新增
    }
    
    return memory
```

#### 2.3 清理过期记忆

**触发时机**: 
1. 每次 Consolidation 前
2. 每次检索前（可选）

```python
def expire_old_memories():
    """清理过期记忆"""
    now = datetime.now()
    
    for pool in ['active', 'archive']:
        for mem_type in ['facts', 'beliefs', 'summaries']:
            path = get_memory_dir() / 'layer2' / pool / f'{mem_type}.jsonl'
            
            if not path.exists():
                continue
            
            memories = load_jsonl(path)
            valid_memories = []
            expired_count = 0
            
            for mem in memories:
                expires_at = mem.get('expires_at')
                
                # 没有过期时间，或未过期
                if expires_at is None or datetime.fromisoformat(expires_at) > now:
                    valid_memories.append(mem)
                else:
                    expired_count += 1
                    # 可选：记录到日志
                    log_expired_memory(mem)
            
            # 保存未过期的记忆
            if expired_count > 0:
                save_jsonl(path, valid_memories)
                print(f"✓ 清理 {expired_count} 条过期记忆 ({mem_type}/{pool})")
```

#### 2.4 过期记忆归档（可选）

```python
def log_expired_memory(memory):
    """记录过期记忆（用于审计）"""
    log_path = get_memory_dir() / 'layer2' / 'expired_log.jsonl'
    
    log_entry = {
        "memory_id": memory['id'],
        "content": memory['content'],
        "created_at": memory['created_at'],
        "expires_at": memory['expires_at'],
        "expired_at": datetime.now().isoformat()
    }
    
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
```

---

## 🔄 工作流程更新

### 更新后的 Consolidation 流程

```
Phase 0: 清理过期记忆（新增）
    ↓
Phase 1: 提取原始记忆
    ├─ 检测时间敏感性（新增）
    └─ 设置 expires_at（新增）
    ↓
Phase 2: 规则过滤
    ↓
Phase 3: 模板提取
    ↓
Phase 4a: LLM 分类
    ↓
Phase 4b: 代码验证
    ↓
Phase 5: 排名
    ├─ 应用访问频率加成（新增）
    └─ 计算最终分数
    ↓
Phase 6: 衰减更新
    ├─ 考虑最后访问时间（新增）
    └─ 最近访问的记忆衰减慢
    ↓
Phase 7: 生成快照
```

### 更新后的检索流程

```
用户查询
    ↓
过滤过期记忆（新增）
    ↓
检索匹配记忆
    ↓
应用访问频率加成（新增）
    ↓
记录访问日志（新增）
    ↓
返回结果
```

---

## 📝 配置更新

### config.json 新增配置

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
  
  // ===== 新增配置 =====
  "access_tracking": {
    "enabled": true,
    "boost_coefficient": 0.1,    // 访问频率加成系数
    "max_boost": 0.5,            // 最大加成
    "log_retention_days": 90     // 访问日志保留天数
  },
  "time_sensitivity": {
    "enabled": true,
    "auto_detect": true,         // 自动检测时间敏感内容
    "cleanup_on_consolidation": true,  // Consolidation 时清理
    "cleanup_on_retrieval": false      // 检索时清理（可选）
  }
}
```

---

## 🛠️ 实现清单

### Phase 1: 访问日志（1-2天）

- [ ] 1.1 添加访问日志文件结构
- [ ] 1.2 实现 `record_access()` 函数
- [ ] 1.3 实现 `update_memory_access_stats()` 函数
- [ ] 1.4 实现 `calculate_access_boost()` 函数
- [ ] 1.5 更新 Phase 5 排名逻辑
- [ ] 1.6 更新记忆条目数据结构（添加新字段）
- [ ] 1.7 测试访问追踪功能

### Phase 2: 时间敏感记忆（1-2天）

- [ ] 2.1 实现 `detect_time_sensitivity()` 函数
- [ ] 2.2 更新 Phase 1 提取逻辑（检测时间敏感性）
- [ ] 2.3 实现 `expire_old_memories()` 函数
- [ ] 2.4 实现 `log_expired_memory()` 函数（可选）
- [ ] 2.5 在 Consolidation 前添加清理步骤
- [ ] 2.6 测试过期清理功能

### Phase 3: 整合测试（1天）

- [ ] 3.1 更新 config.json 配置
- [ ] 3.2 迁移现有记忆数据（添加新字段）
- [ ] 3.3 端到端测试
- [ ] 3.4 性能测试
- [ ] 3.5 文档更新

---

## 💡 设计考虑

### 1. 访问频率加成的平衡

**问题**: 访问频率高 ≠ 一定重要

**解决方案**:
- 加成系数设为 0.1（可配置）
- 最大加成限制为 0.5
- 基础分数仍由 importance 和 confidence 决定

**示例**:
```
记忆 A: importance=0.8, confidence=0.9, access_boost=0.2
  → base_score = 0.72
  → final_score = 0.72 * 1.2 = 0.864

记忆 B: importance=0.5, confidence=0.8, access_boost=0.5
  → base_score = 0.40
  → final_score = 0.40 * 1.5 = 0.60

记忆 A 仍然排名更高（重要性优先）
```

### 2. 时间敏感检测的准确性

**问题**: 自动检测可能误判

**解决方案**:
- 保守策略：只标记明确的时间敏感词
- 提供手动标记接口（未来）
- 过期后不删除，只是不参与检索（可恢复）

### 3. 访问日志的存储成本

**问题**: 访问日志可能快速增长

**解决方案**:
- 定期清理旧日志（默认保留 90 天）
- 只保留统计数据（access_count, last_accessed）
- 可选：压缩归档旧日志

### 4. 衰减与访问的关系

**问题**: 常访问的记忆是否应该衰减慢？

**解决方案**:
```python
def phase6_decay_with_access(memory):
    """衰减时考虑访问时间"""
    last_accessed = memory.get('last_accessed')
    
    if last_accessed:
        days_since_access = (datetime.now() - datetime.fromisoformat(last_accessed)).days
        
        # 最近 7 天访问过，衰减慢
        if days_since_access < 7:
            decay_factor = 0.99  # 几乎不衰减
        else:
            decay_factor = memory['decay_rate']
    else:
        decay_factor = memory['decay_rate']
    
    memory['confidence'] *= decay_factor
```

---

## 📊 预期效果

### 访问日志

**Before (v1.0)**:
```
所有记忆按 importance * confidence 排序
常用记忆和不常用记忆权重相同
```

**After (v1.1)**:
```
常用记忆获得加成，排名提升
示例：
- "Ktao 喜欢轻松互动" (访问 20 次) → boost +0.2
- "Ktao 的生日是..." (访问 1 次) → boost +0.01
```

### 时间敏感记忆

**Before (v1.0)**:
```
"明天3点开会" 永久保留
过时信息混淆 AI 判断
```

**After (v1.1)**:
```
"明天3点开会" 会议后自动过期
Layer 1 快照更干净，更相关
```

---

## 🚀 下一步

1. **你确认设计方案**
2. **我开始实现 Phase 1（访问日志）**
3. **测试通过后实现 Phase 2（时间敏感）**
4. **整合测试**
5. **更新文档和 SKILL.md**

**注意**: 不会更新 GitHub，只在本地实现和测试。

---

**设计完成，等待你的反馈！** 🦞
