# Memory System v1.2 优化方案

> 整理时间: 2026-02-11
> 当前版本: v1.1.7
> 目标版本: v1.2.0 (脱脂版)
> 状态: 活跃池 98 条，系统运行正常

---

## 🔴 架构级问题 - "四大肉瘤"深度剖析

### 肉瘤 1: "双重复记"的存储冗余 (Double-Bookkeeping)

**现状诊断**:
```
当前存储结构:
├── layer1/snapshot.md          # 人读版（4.7KB）
├── layer2/active/facts.jsonl   # 机读版（73条）
├── layer2/active/beliefs.jsonl # 机读版（9条）
├── layer2/active/summaries.jsonl # 机读版（16条）
├── layer2/entities/            # 实体档案（113个）
└── layer2/index/               # 索引文件
```

**问题本质**:
- 每次更新一个 Fact，需要操作 3 个地方：JSONL + snapshot.md + index
- snapshot.md 是 Phase 7 生成的"人读版"，但实际上 LLM 注入时又要重新解析
- 这就像医生写病历：纸质版 + 电脑版 + 家属版，三份同步维护

**冗余成本**:
- IO 操作: 每次 consolidation 至少 6 次文件写入
- 数据一致性风险: 三份数据可能不同步
- 维护成本: 任何格式变更都要改三处

**v1.2 解决方案**:
```python
# 废弃 snapshot.md 作为持久化环节
# 改为即时生成的 viewer 函数

def generate_snapshot_on_demand(memory_dir, token_budget=2000):
    """按需生成快照，不持久化"""
    facts = load_jsonl(f"{memory_dir}/layer2/active/facts.jsonl")
    # 直接从 JSONL 生成，不写文件
    return format_for_injection(facts, token_budget)
```

**预期收益**:
- IO 操作减少 33%
- 消除数据不一致风险
- 代码维护量减少

---

### 肉瘤 2: "全量扫描"的衰减计算 (O(n) Calc Tax)

**现状诊断**:
```python
# Phase 5 当前逻辑（伪代码）
def apply_decay():
    for memory in ALL_98_MEMORIES:  # O(n) 全量扫描
        memory.score *= decay_rate
        if memory.score < 0.05:
            archive(memory)
```

**问题本质**:
- 每次 consolidation 都计算全部 98 条（未来可能上千条）的衰减
- 大多数 Facts 根本没变，但每次都重新计算
- 这是 CPU 空烧，尤其在 VPS (2C/0.5G) 上

**冗余成本**:
- 计算量: O(n) 每次，n 会持续增长
- 无效计算: 90% 的记忆没被访问，但都要算一遍

**v1.2 解决方案**:
```python
# 引入脏标记 (Dirty Bit) 机制

def apply_decay_smart():
    dirty_memories = get_dirty_memories()  # 只获取被标记的
    
    for memory in dirty_memories:  # O(k), k << n
        memory.score *= decay_rate
        memory.dirty = False
    
    # 大结算周期（每周一次）才全量计算
    if is_weekly_settlement():
        for memory in ALL_MEMORIES:
            memory.score *= weekly_decay_rate

def mark_dirty(memory_id):
    """在访问/引用时标记"""
    memory.dirty = True
    memory.last_touched = now()
```

**预期收益**:
- 日常计算量从 O(n) 降到 O(k)，k 约为 n 的 10%
- CPU 使用降低 80%+
- 响应速度提升

---

### 肉瘤 3: "静态快照"的 Context 浪费 (The 2000-Token Tax)

**现状诊断**:
```markdown
# 当前 snapshot.md 内容（4.7KB，约 1500 tokens）
- 用户名字是某用户...
- Tkao是Ktao的数字镜像...
- 我去，真不行了，困死了啊  ← 这条和当前对话有关吗？
- 个人项目：个人医学AI助手... ← 聊代码时需要这个吗？
```

**问题本质**:
- 固定注入 2000 tokens，不管当前对话主题是什么
- 聊代码时，"某用户大三学生"和"喜欢吃什么"也被塞进去
- 这是 Context 窗口的浪费

**冗余成本**:
- Token 浪费: 每次对话浪费 1000-1500 tokens 在无关信息上
- 注意力稀释: LLM 被迫处理无关信息，影响回复质量

**v1.2 解决方案**:
```python
# 基于关键词的动态注入

def dynamic_injection(user_message, memory_dir, max_tokens=400):
    """只注入与当前对话相关的记忆"""
    
    # 1. 提取用户消息中的实体/关键词
    entities = extract_entities(user_message)
    keywords = extract_keywords(user_message)
    
    # 2. 从倒排索引中检索相关记忆
    relevant_memories = []
    for entity in entities:
        relevant_memories.extend(inverted_index.get(entity, []))
    
    # 3. 按相关度排序，截取 top-k
    ranked = rank_by_relevance(relevant_memories, user_message)
    
    # 4. 控制在 400 tokens 以内
    return format_injection(ranked[:10], max_tokens=400)
```

**预期收益**:
- 注入量从 2000 tokens 压缩到 400 tokens（精准注入）
- 剩余 1600 tokens 留给更相关的 Session 历史
- 回复质量提升（注意力集中在相关信息上）

---

### 肉瘤 4: "逻辑筛选"的 LLM 滥用 (Financial Redundancy)

**现状诊断**:
```python
# Phase 2 当前逻辑
def filter_segments(segments):
    for seg in segments:
        if is_ambiguous(seg):  # 0.2~0.5 区间
            # 调用 LLM 判断"哈哈"是不是废话
            result = call_llm(f"这条内容值得记忆吗？{seg}")
```

**问题本质**:
- 用 LLM 判断"哈哈"、"好的"、"嗯"是不是废话
- 这是"大炮轰蚊子"，烧钱又慢
- v1.1.7 虽然扩大了 LLM 触发区间，但规则前置器还不够强

**冗余成本**:
- API 费用: 每次 consolidation 约 1800 tokens，大部分花在低级判别上
- 延迟: LLM 调用增加 2-5 秒延迟

**v1.2 解决方案**:
```python
# 极度强化规则前置器

CHAT_FILTER_PATTERNS = [
    # 扩充到 50+ 条规则
    r'^(哈哈|嗯|好的|ok|行|嗯嗯|哦|啊)+$',
    r'^(谢谢|感谢|辛苦了|不客气)+$',
    r'^[\U0001F600-\U0001F64F]+$',  # 纯 emoji
    # ... 更多规则
]

def rule_filter_enhanced(segment):
    """增强版规则过滤"""
    # 1. 正则匹配（0 Token）
    for pattern in CHAT_FILTER_PATTERNS:
        if re.match(pattern, segment):
            return False, 0.0  # 直接丢弃
    
    # 2. 朴素贝叶斯分类器（0 Token）
    if naive_bayes_classifier.predict(segment) == 'noise':
        return False, 0.1
    
    # 3. 只有真正模糊的才调用 LLM
    confidence = rule_confidence(segment)
    if 0.3 < confidence < 0.6:  # 真正的灰色地带
        return call_llm_filter(segment)
    
    return True, confidence
```

**预期收益**:
- LLM 调用减少 70%+
- API 费用从 1800 tokens/天 降到 500 tokens/天
- 延迟降低 50%+

---

## 🔴 P0 - 紧急（计划 2/12 解决）

### 1. Phase 3 提取质量优化
**问题**: 实体/关键词提取精度不够
**与肉瘤关联**: 肉瘤 3（动态注入依赖精准的实体提取）
**解决方向**:
- 优化 `extract_entities()` 函数
- 增强 LLM 提取的触发条件
- 改进中文分词算法

### 2. Summary 语义整合
**问题**: 摘要生成的语义聚合逻辑不够智能
**与肉瘤关联**: 肉瘤 1（减少冗余存储后，Summary 更重要）
**解决方向**:
- 改进 `generate_summaries()` 函数
- 增加语义相似度计算

---

## 🟡 P1 - 重要（年前有空）

### 3. 肉瘤 1 修复: 废弃双重存储
**工作量**: 2-3 小时
**步骤**:
1. 删除 Phase 7 的 snapshot.md 写入逻辑
2. 实现 `generate_snapshot_on_demand()` 函数
3. 修改 OpenClaw 集成，改为动态生成

### 4. 肉瘤 2 修复: 引入脏标记
**工作量**: 3-4 小时
**步骤**:
1. 在记忆结构中添加 `dirty` 字段
2. 修改 `record-access` 命令，自动标记 dirty
3. 修改 Phase 5，只处理 dirty 记忆
4. 添加周结算逻辑

### 5. 肉瘤 3 修复: 动态注入
**工作量**: 4-5 小时
**步骤**:
1. 实现简易倒排索引
2. 实现 `dynamic_injection()` 函数
3. 修改 OpenClaw 集成，改为动态注入
4. 测试不同场景的注入效果

### 6. 肉瘤 4 修复: 强化规则前置器
**工作量**: 2-3 小时
**步骤**:
1. 扩充 `CHAT_FILTER_PATTERNS` 到 50+ 条
2. 实现简易朴素贝叶斯分类器
3. 收窄 LLM 触发区间

### 7. Layer 3 数据源接入
**问题**: Consolidate 无法自动读取 OpenClaw session
**工作量**: 3-4 小时

### 8. IO 竞态 → SQLite
**问题**: JSONL 并发读写竞态
**工作量**: 5-6 小时
**与肉瘤关联**: 肉瘤 1（单一数据源后，SQLite 更合适）

---

## 🟢 P2 - 一般（年后）

### 9. 语义嵌入增强检索
### 10. 增量索引更新
### 11. 多 Agent 记忆共享
### 12. 可视化记忆图谱

---

## 📊 v1.2 目标指标

| 指标 | v1.1.7 现状 | v1.2 目标 | 改进幅度 |
|------|-------------|-----------|----------|
| 注入 Token | ~1500 | ~400 | -73% |
| IO 操作/次 | 6+ | 2 | -67% |
| LLM 调用 Token/天 | ~1800 | ~500 | -72% |
| Phase 5 计算量 | O(n) | O(k), k≈0.1n | -90% |
| 数据源数量 | 3 (JSONL+MD+Index) | 1 (SQLite) | -67% |

---

## 🎯 v1.2 开发路线

### 阶段 1: 脱脂手术（2/12-2/14）
1. ✅ P0: Phase 3 提取质量
2. ✅ P0: Summary 语义整合
3. 肉瘤 4: 强化规则前置器（最简单，先做）

### 阶段 2: 架构重构（2/15-2/18）
4. 肉瘤 1: 废弃双重存储
5. 肉瘤 2: 引入脏标记
6. 肉瘤 3: 动态注入

### 阶段 3: 基础设施（年后）
7. IO 竞态 → SQLite
8. Layer 3 数据源接入

---

## 💡 Crabby 的核心洞察

> "好的记忆系统应该是'悄无声息的按需调用'。"

**翻译成技术语言**:
1. **按需** = 动态注入，不是静态快照
2. **悄无声息** = 规则优先，LLM 兜底
3. **调用** = 检索驱动，不是全量加载

> "你要是能把注入量从 2000 tokens 压缩到精准的 400 tokens，同时把 IO 操作次数降下来，你这套系统才叫实现了医学上的'微创与精准'。"

**这就是 v1.2 的核心目标**:
- 2000 → 400 tokens（精准注入）
- 6+ → 2 IO 操作（微创）
- O(n) → O(k) 计算（高效）

---

## ✅ 已解决的问题（v1.1.x 历史）

[保持原有内容不变]

---

*文档维护: Tkao*
*最后更新: 2026-02-11*
*感谢 Crabby 的深度剖析 🦀*
