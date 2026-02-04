---
name: memory-system
version: 1.0.0
description: 三层记忆架构系统，模拟人类记忆机制。自动提取、结构化存储、智能衰减、动态快照。让 AI Agent 拥有真正的长期记忆。
metadata:
  clawdbot:
    emoji: "🧠"
    requires:
      bins: ["python3", "jq"]
    install:
      - id: "init"
        kind: "script"
        command: "python3 scripts/memory.py init"
        label: "初始化记忆系统目录结构"
---

# Memory System v1.0 — 三层记忆架构

> **让 AI 从金鱼变成大象。**

一个完整的 AI Agent 记忆系统，基于认知科学原理设计，实现：
- 🧠 **三层记忆架构**：工作记忆 → 长期记忆 → 原始日志
- ⚡ **自动整合**：每日 Consolidation，无需手动维护
- 🎯 **智能衰减**：重要信息永不遗忘，琐碎信息自然淡化
- 📊 **结构化存储**：Facts / Beliefs / Summaries 分类管理
- 🔍 **高效检索**：多维索引，毫秒级响应

---

## 设计理念

### 为什么需要这个系统？

| 问题 | 现状 | 本系统解决方案 |
|------|------|---------------|
| AI 忘记重要信息 | "我对花生过敏"说一次就忘 | **重要性评分**：语义判断，自动识别关键信息 |
| 记忆越来越乱 | MEMORY.md 越写越长，找不到重点 | **自动整合**：每日 Consolidation，结构化存储 |
| Token 消耗失控 | 每次对话都要加载全部记忆 | **分层注入**：Layer 1 快照控制在 2000 tokens |
| 旧信息堆积 | 过时信息占用空间和注意力 | **智能衰减**：自动降权，分池管理 |

### 核心原则

```
1. 检索优先 — 不是"记得多"，而是"找得准"
2. 写复杂读简单 — 复杂逻辑在写入时处理，读取 O(1)
3. 重要性由语义决定 — 不依赖使用频率，不漏重要信息
4. 自动衰减 — 旧记忆自动降权，不依赖手动清理
```

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     Layer 1: 工作记忆                        │
│                   (snapshot.md, ~2000 tokens)                │
│         每次对话自动注入，包含最重要的上下文                    │
└─────────────────────────────────────────────────────────────┘
                              ↑
                    Consolidation Phase 7 生成
                              ↑
┌─────────────────────────────────────────────────────────────┐
│                     Layer 2: 长期记忆                        │
│              (facts.jsonl / beliefs.jsonl / summaries.jsonl) │
│                                                             │
│   ┌─────────────┐              ┌─────────────┐              │
│   │   active/   │  ←— 衰减 —→  │  archive/   │              │
│   │  (活跃池)    │    score     │  (归档池)    │              │
│   │  参与检索    │    < 0.05    │  冷藏保存    │              │
│   └─────────────┘              └─────────────┘              │
│                                                             │
│   entities/     — 实体档案（人物、地点、项目）                  │
│   index/        — 多维索引（关键词、时间线、关系）              │
└─────────────────────────────────────────────────────────────┘
                              ↑
                    Consolidation Phase 1-6 处理
                              ↑
┌─────────────────────────────────────────────────────────────┐
│                     Layer 3: 原始日志                        │
│                    (OpenClaw Session Transcript)             │
│                  只读取，不修改，完整保留原始对话               │
└─────────────────────────────────────────────────────────────┘
```

---

## 文件结构

```
workspace/memory/
├── config.json                    # 系统配置
├── layer1/
│   └── snapshot.md                # 工作记忆快照（自动生成）
├── layer2/
│   ├── active/                    # 活跃池（参与检索和衰减）
│   │   ├── facts.jsonl            # 事实库
│   │   ├── beliefs.jsonl          # 推断库
│   │   └── summaries.jsonl        # 摘要库
│   ├── archive/                   # 归档池（冷藏保存）
│   │   ├── facts.jsonl
│   │   ├── beliefs.jsonl
│   │   └── summaries.jsonl
│   ├── entities/                  # 实体档案
│   │   ├── _index.json            # 实体索引
│   │   └── {entity_id}.json       # 单个实体详情
│   └── index/                     # 检索索引
│       ├── keywords.json          # 关键词 → 记忆ID
│       ├── timeline.json          # 时间 → 记忆ID
│       └── relations.json         # 实体 → 相关记忆
└── state/
    ├── consolidation.json         # Consolidation 状态（支持断点续传）
    └── rankings.json              # 当前排名快照
```

---

## 记忆类型

### Facts（事实）
用户明确陈述的信息，置信度 = 1.0

```json
{
  "id": "f_20260204_001",
  "content": "用户对花生过敏",
  "importance": 1.0,
  "score": 0.95,
  "entities": ["用户"],
  "created": "2026-02-04T10:30:00Z",
  "source": "session_abc123:15"
}
```

### Beliefs（推断）
基于对话推断的信息，置信度 < 1.0

```json
{
  "id": "b_20260204_001",
  "content": "用户可能在科技公司工作",
  "confidence": 0.6,
  "importance": 0.5,
  "score": 0.72,
  "basis": "提到在北京工作，经常开会",
  "entities": ["用户"],
  "created": "2026-02-04T10:30:00Z"
}
```

### Summaries（摘要）
多个相关 facts 的聚合

```json
{
  "id": "s_20260204_001",
  "content": "用户是学生，对 AI 技术感兴趣，正在开发个人项目",
  "importance": 0.9,
  "score": 0.88,
  "source_facts": ["f_001", "f_015", "f_023"],
  "entities": ["用户", "个人项目"],
  "created": "2026-02-04T10:30:00Z"
}
```

---

## 重要性评分机制

### 内在重要性（信息本身的性质）

| 类型 | 分数 | 示例 |
|------|------|------|
| 身份/健康/安全 | 1.0 | "我对花生过敏"、"我叫张三" |
| 偏好/关系/状态变更 | 0.8 | "我讨厌香菜"、"我换工作了" |
| 一般事实 | 0.5 | "我昨天去了北京" |
| 临时信息 | 0.2 | "今天下午开会" |

### 外在信号（用户表达方式）

| 信号 | 加成 |
|------|------|
| "记住"、"以后都" | +0.5 |
| "重要"、"关键" | +0.3 |
| 重复提及 | +0.2 |
| "顺便说一下" | -0.2 |

### 评分公式

```python
importance = min(1.0, intrinsic_score + explicit_signal)
```

---

## 衰减机制

### 衰减率（每日）

| 类型 | 基础衰减 | 半衰期 |
|------|---------|--------|
| Fact | 0.8% | ~87 天 |
| Belief | 7% | ~10 天 |
| Summary | 2.5% | ~28 天 |

### Importance 影响衰减

```python
actual_decay = base_decay × (1 - importance × 0.5)
```

**示例**：
- importance=1.0 的 fact：实际衰减 0.4%/天，半衰期 ~174 天
- importance=0.5 的 fact：实际衰减 0.6%/天，半衰期 ~116 天

### 归档规则

```
score < 0.05 → 移入 archive/（冷藏，不再参与检索）
```

---

## Consolidation 流程

每日自动执行，将原始对话转化为结构化记忆。

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: 轻量全量                                          │
│  ─────────────────                                          │
│  • 读取今日对话（OpenClaw Session）                          │
│  • 按规则切分为语义片段                                      │
│  • 标记类型：陈述/问题/指令/闲聊                              │
│  • 成本：0 tokens（纯规则）                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: 重要性筛选                                        │
│  ─────────────────                                          │
│  • 模型判断哪些片段值得长期记忆                               │
│  • 标注 importance 等级                                     │
│  • 成本：~700 tokens                                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 3: 深度提取                                          │
│  ─────────────────                                          │
│  • 将筛选出的片段转为结构化 facts/beliefs                     │
│  • 识别实体（人名、地名、项目名）                             │
│  • 成本：~500 tokens                                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 4: Layer 2 维护                                      │
│  ─────────────────                                          │
│  • 4a: Facts 去重合并（同实体同属性 → 合并，保留历史）         │
│  • 4b: Beliefs 验证（被新 fact 证实 → 升级为 fact）          │
│  • 4c: Summaries 生成（同主题 ≥3 facts → 生成摘要）          │
│  • 4d: Entities 更新（维护实体档案）                         │
│  • 成本：~400 tokens（条件触发）                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 5: 权重更新                                          │
│  ─────────────────                                          │
│  • 所有活跃记忆按衰减率降权                                   │
│  • score < 0.05 → 移入 archive/                             │
│  • 成本：0 tokens（纯规则）                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 6: 索引更新                                          │
│  ─────────────────                                          │
│  • 增量更新 keywords/timeline/relations 索引                 │
│  • 成本：0 tokens（纯规则）                                  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Phase 7: Layer 1 快照                                      │
│  ─────────────────                                          │
│  • 按 score 排名生成工作记忆快照                              │
│  • 控制在 ~2000 tokens                                      │
│  • 排名靠前 → 内容更丰富                                     │
│  • 成本：~200 tokens（排名变化时）                            │
└─────────────────────────────────────────────────────────────┘

总成本：~1800 tokens/天
```

### 触发机制

| 触发方式 | 条件 |
|---------|------|
| 定时触发 | 每天凌晨 3 点（Cron） |
| 兜底触发 | 超过 48 小时未执行 |
| 手动触发 | `memory.py consolidate --force` |

### 断点续传

如果执行中断，下次自动从断点继续：

```json
// state/consolidation.json
{
  "last_run": "2026-02-04T03:00:00Z",
  "last_success": "2026-02-04T03:00:00Z",
  "current_phase": null,
  "phase_data": {},
  "retry_count": 0
}
```

### 处理策略：规则优先，LLM 兜底

**核心原则：能用代码解决的不用 LLM，省 Token。**

| Phase | 简单情况（代码） | 复杂情况（LLM） |
|-------|-----------------|----------------|
| Phase 1 收集 | ✅ 代码切分 | ✅ 代码切分 |
| Phase 2 筛选 | ✅ 规则过滤 | 规则无法判断时 → LLM |
| Phase 3 提取 | ✅ 正则/模板匹配 | 复杂语义 → LLM |
| Phase 4a Fact | ✅ 代码去重 | ✅ 代码去重 |
| Phase 4b Belief | ✅ 代码匹配证据 | 模糊情况 → LLM |
| Phase 4c Summary | - | LLM 生成 |
| Phase 5 衰减 | ✅ 代码计算 | ✅ 代码计算 |
| Phase 6 索引 | ✅ 代码重建 | ✅ 代码重建 |
| Phase 7 快照 | ✅ 代码生成框架 | 可选 LLM 润色 |

#### Phase 2 规则过滤示例

```python
def rule_filter(content):
    # 直接丢弃
    if len(content) < 10:
        return False, "太短"
    if content.strip() in ["好的", "嗯", "OK", "好", "行"]:
        return False, "无意义回复"
    if is_greeting(content):
        return False, "问候语"
    
    # 直接保留
    if "记住" in content or "重要" in content:
        return True, "用户标记重要"
    if contains_time_reference(content):
        return True, "时间敏感"
    
    # 无法判断 → 交给 LLM
    return None, "需要 LLM 判断"
```

#### Phase 3 模板匹配示例

```python
PATTERNS = {
    r"我是(.+)": ("fact", "identity"),
    r"我叫(.+)": ("fact", "name"),
    r"我喜欢(.+)": ("fact", "preference"),
    r"(明天|下周.?)(.+)": ("fact", "schedule"),
}

def template_extract(content):
    for pattern, (mem_type, category) in PATTERNS.items():
        match = re.search(pattern, content)
        if match:
            return {"type": mem_type, "category": category, "value": match.group(1)}
    return None  # 交给 LLM
```

#### Token 节省效果

| 场景 | 纯 LLM 方案 | 规则优先方案 | 节省 |
|------|------------|-------------|------|
| 10 条记忆 | ~2000 tokens | ~200 tokens | 90% |
| 50 条记忆 | ~8000 tokens | ~500 tokens | 94% |
| 100 条记忆 | ~15000 tokens | ~800 tokens | 95% |

---

## Layer 1 快照结构

```markdown
# 工作记忆快照
> 生成时间: 2026-02-04T03:00:00Z | 记忆数: 156 | 活跃: 142 | 归档: 14

## 身份
- 名字: Tkao
- 定位: 用户 的数字镜像

## 用户
- 名字: 张三 (用户)
- 专业: 计算机科学大三
- 核心项目: 个人项目

## 约束
- 隐私边界: 不透露项目细节、家庭信息、经济状况
- 交互风格: 轻松友好，效率优先

## 核心记忆 (Top 5)
1. [1.0] 用户对花生过敏
2. [0.95] 用户正在开发个人项目，基于 某平台
3. [0.91] 用户希望经济独立，随心玩转 AI 工具
4. [0.88] 用户代码能力有限(⭐⭐)，依赖 AI 辅助
5. [0.85] 用户在某大学就读

## 近期要点 (3天内)
- 2026-02-04: 完成记忆系统 Consolidation 设计
- 2026-02-03: 讨论三层架构和 Router 逻辑
- 2026-02-02: Moltbook 社交任务配置完成

## 索引
[完整记忆库: 156 条 | 实体: 23 个 | 主题: 12 类]
使用 memory_search 检索详细信息
```

---

## 使用方法

### 初始化

```bash
# 创建目录结构和默认配置
python3 scripts/memory.py init
```

### 手动执行 Consolidation

```bash
# 完整流程
python3 scripts/memory.py consolidate

# 强制执行（忽略时间检查）
python3 scripts/memory.py consolidate --force

# 只执行某个阶段（调试用）
python3 scripts/memory.py consolidate --phase 2
```

### 手动添加记忆

```bash
# 添加 fact
python3 scripts/memory.py capture "用户对花生过敏" \
  --type fact \
  --importance 1.0 \
  --entities "用户"

# 添加 belief
python3 scripts/memory.py capture "用户可能喜欢咖啡" \
  --type belief \
  --confidence 0.6 \
  --importance 0.5
```

### 查看状态

```bash
# 系统状态
python3 scripts/memory.py status

# 统计信息
python3 scripts/memory.py stats

# 输出示例:
# 📊 Memory System Stats
# ══════════════════════
# Total: 156 memories
# Active: 142 | Archive: 14
# 
# By Type:
#   Facts: 89 (57%)
#   Beliefs: 42 (27%)
#   Summaries: 25 (16%)
# 
# By Importance:
#   Critical (0.9-1.0): 12
#   High (0.7-0.9): 45
#   Medium (0.4-0.7): 67
#   Low (0-0.4): 32
# 
# Last Consolidation: 2026-02-04T03:00:00Z
# Next Scheduled: 2026-02-05T03:00:00Z
```

### 维护命令

```bash
# 重建索引
python3 scripts/memory.py rebuild-index

# 验证数据完整性
python3 scripts/memory.py validate

# 手动归档
python3 scripts/memory.py archive <memory_id>
```

---

## 配置说明

```json
// memory/config.json
{
  "version": "1.0",
  
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
    "layer1_total": 2000,
    "layer1_top1": 0.4,
    "layer1_top2": 0.25,
    "layer1_top3": 0.15,
    "layer1_rest": 0.2
  },
  
  "consolidation": {
    "schedule": "0 3 * * *",
    "fallback_hours": 48,
    "model": "default"
  },
  
  "importance_rules": {
    "identity_health_safety": 1.0,
    "preference_relation_status": 0.8,
    "general_fact": 0.5,
    "temporary": 0.2
  }
}
```

---

## 与 OpenClaw 集成

### 1. 配置 Layer 1 自动注入

在 OpenClaw 配置中添加：

```json
{
  "agents": {
    "main": {
      "systemPromptFiles": [
        "memory/layer1/snapshot.md"
      ]
    }
  }
}
```

### 2. 配置定时 Consolidation

添加 Cron Job：

```json
{
  "name": "Memory Consolidation",
  "schedule": {"kind": "cron", "expr": "0 3 * * *"},
  "payload": {"kind": "systemEvent", "text": "执行记忆整合: python3 scripts/memory.py consolidate"},
  "sessionTarget": "main"
}
```

### 3. 配置 Heartbeat 兜底

在 HEARTBEAT.md 中添加：

```markdown
## Memory Consolidation 检查
如果距离上次 Consolidation > 48 小时：
  执行 `python3 scripts/memory.py consolidate`
```

### 4. 配置检索规则

在 AGENTS.md 中添加：

```markdown
## 记忆检索规则

### 自动注入
- Layer 1 snapshot 已通过 systemPromptFiles 自动注入

### 主动检索触发条件
当用户消息包含以下情况时，调用 memory_search：
- 提到过去："之前"、"上次"、"以前"
- 询问偏好："我喜欢"、"我讨厌"
- 涉及人物：人名、关系词
- 涉及项目：项目名、任务名
- 显式请求："你还记得"、"帮我回忆"
```

---

## 设计亮点

### 1. 认知科学启发

| 人类记忆 | 本系统实现 |
|---------|-----------|
| 工作记忆容量有限 | Layer 1 控制在 2000 tokens |
| 睡眠时整合记忆 | 冷淡期执行 Consolidation |
| 重要的事记得更牢 | importance 影响衰减率 |
| 遗忘是自然的 | 自动衰减 + 归档机制 |
| 关联记忆更容易回忆 | 实体关系索引 |

### 2. 工程优化

| 优化点 | 实现方式 |
|--------|---------|
| 成本控制 | 分层提取，只深度处理重要内容 |
| 性能优化 | 增量索引更新，条件触发生成 |
| 可靠性 | 断点续传，失败重试 |
| 可维护性 | 结构化存储，清晰的文件组织 |

### 3. 与现有系统兼容

- 不修改 OpenClaw 源码
- 利用现有的 memory_search 能力
- 通过配置和 AGENTS.md 集成

---

## 性能指标

| 指标 | 目标 | 说明 |
|------|------|------|
| Consolidation 成本 | ~1800 tokens/天 | 7 Phase 总和 |
| Layer 1 大小 | ~2000 tokens | 每次对话注入 |
| 检索延迟 | <100ms | 索引查询 |
| 活跃池上限 | ~200 条 | 动态平衡 |

---

## 路线图

### v1.0（当前）
- [x] 三层架构设计
- [x] Consolidation 7 Phase 流程
- [x] 重要性评分机制
- [x] 衰减和归档机制
- [ ] 核心脚本实现
- [ ] 测试和验证

### v1.1（计划）
- [ ] 访问记录和访问加权
- [ ] 归档内容激活机制
- [ ] 从现有 MEMORY.md 迁移工具

### v2.0（远期）
- [ ] 语义嵌入增强检索
- [ ] 多 Agent 记忆共享
- [ ] 可视化记忆图谱

---

## 参考文档

- [设计文档](docs/design.md) — 完整的架构设计说明
- [Consolidation 报告](docs/consolidation.md) — 7 Phase 详细实现
- [API 参考](docs/api.md) — CLI 命令和配置说明

---

## 致谢

本系统设计参考了：
- 认知科学中的记忆整合理论
- Ebbinghaus 遗忘曲线
- 现有 AI Agent 记忆系统（memory-system-v2, triple-memory）

---

**Memory System v1.0 — 让 AI 拥有真正的记忆。** 🧠
