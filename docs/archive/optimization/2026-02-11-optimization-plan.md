# 记忆系统 v1.1.8 优化方案

## 日期：2026-02-11

## 背景
Crabby 对 v1.1.7 提出了"四大肉瘤"批评，结合实际代码分析后整理出以下优化方案。

---

## Crabby 的四个批评点

### 1. 双重复记的存储冗余
**Crabby 说**：JSONL + Markdown + Python 脚本，每次更新要操作三个地方。

**实际情况**：
- Layer 2 JSONL（活跃记忆）和 Layer 3 Markdown（冷归档）职责不同，不算冗余
- 真正冗余的是 `workspace/MEMORY.md`，手动维护，可以自动生成

**结论**：部分正确

### 2. 全量扫描的衰减计算
**Crabby 说**：每次 Consolidation 都算所有记录的衰减，大部分没变。

**实际情况**：确实如此，O(n) 计算浪费 CPU。

**解决方案**：引入 Dirty Bit，只计算被访问/新增的记录。

**结论**：完全正确

### 3. 静态快照的 Context 浪费
**Crabby 说**：固定 2000 tokens，聊代码时还塞"大三学生"进去。

**实际情况**：
- `v1_2_associative_recall.py` 已实现关联唤醒
- 但还没替代静态注入，没真正用起来

**解决方案**：动态注入替代静态快照，基于当前对话关键词检索相关记忆。

**结论**：完全正确

### 4. LLM 滥用判断废话
**Crabby 说**：用 LLM 判断"哈哈"是不是废话，大炮轰蚊子。

**实际情况**：
- `EXPLICIT_SIGNALS` 和 `CHAT_FILTER_PATTERNS` 已有规则前置
- 但覆盖不够全面

**解决方案**：扩充规则到 50+ 条，LLM 只处理"模糊"内容。

**结论**：部分正确（已有机制，需加强）

---

## 优化优先级

| 优先级 | 任务 | 难度 | 回报 | 状态 |
|--------|------|------|------|------|
| P0 | 动态注入替代静态快照 | ⭐⭐ | ⭐⭐⭐ | 待实现 |
| P1 | Dirty Bit 脏标记 | ⭐ | ⭐⭐ | 待实现 |
| P2 | 规则前置器扩充 | ⭐ | ⭐⭐ | 待实现 |
| P3 | MEMORY.md 自动生成 | ⭐ | ⭐ | 可选 |

---

## P0：动态注入方案设计

### 目标
从固定 2000 tokens 静态快照 → 精准 400 tokens 动态检索

### 实现思路
```
用户输入 → 提取关键词/实体 → 检索相关记忆 → 注入 Context
```

### 关键模块
1. **关键词提取**：从当前对话提取实体（已有 entities 字段）
2. **倒排索引**：按 entity 建立索引，O(1) 查找
3. **相关性排序**：结合 importance、access_count、时间衰减
4. **Token 预算**：限制注入量 ≤ 500 tokens

### 与现有模块的关系
- `v1_2_associative_recall.py`：已实现关联唤醒，可复用
- `router_search()`：已有检索逻辑，需改造为自动注入

---

## P1：Dirty Bit 方案设计

### 目标
避免每次 Consolidation 全量计算衰减

### 实现思路
```python
# 记忆结构新增字段
{
    "dirty": true,  # 是否需要重新计算
    "last_calc": "2026-02-11T07:00:00Z"  # 上次计算时间
}

# Consolidation 逻辑
for memory in memories:
    if memory.dirty or (now - memory.last_calc > 7_days):
        recalculate_decay(memory)
        memory.dirty = False
        memory.last_calc = now
```

### 触发 dirty=true 的条件
- 被 search 命中
- 被 capture 引用
- 手动更新

---

## P2：规则前置器扩充

### 当前规则数量
- `EXPLICIT_SIGNALS`：~15 条
- `CHAT_FILTER_PATTERNS`：~10 条

### 目标
扩充到 50+ 条，覆盖：
- 更多语气词（嗯、啊、哦、呵呵、嘿嘿）
- 更多确认词（好的、收到、明白、OK）
- 更多系统消息模式
- 更多闲聊模式

### 可选：朴素贝叶斯分类器
```python
# 训练数据：历史 capture 的 pass/reject 记录
# 特征：词频、长度、标点、时间段
# 输出：valuable_probability
```

---

## 核心问题

**记忆系统还没真正"上线"到 OpenClaw 的注入流程。**

当前状态：
- ✅ 手动 capture/search 可用
- ❌ 没有自动注入到对话 Context
- ❌ 没有自动从对话中提取记忆

这才是最大的"冗余"——系统存在但没用起来。

---

## 下一步行动

1. 确认优先级顺序
2. 从 P0（动态注入）开始实现
3. 每完成一个优化点，更新版本号

---

*文档创建：2026-02-11 07:20 UTC*
