# 决策日志

记录记忆系统开发过程中的想法、决策、结论。

---

### [decision] 2026-02-12 00:32
四大优化优先级确定：脏标记 > 规则强化 > 单一数据源 > 动态注入

---

### [idea] 2026-02-12 00:32
建立"决策日志"专用类型，讨论结论存 facts 而非大文档，便于 search 快速定位

---

### [decision] 2026-02-11
四大肉瘤分析：①双重复记 ②全量扫描 ③静态快照 ④LLM滥用。分析结论见 docs/v1.2-optimization-plan.md

---

### [decision] 2026-02-12 11:31
v1.2.0 完成：废话前置过滤器(is_noise)+inject命令。脏标记和单一数据源暂缓(101条记忆规模收益低)。下一步：QMD集成+动态注入

---

### [decision] 2026-02-12 12:02
v1.2.0 QMD集成完成：qmd_search+router_search增强+export-qmd命令。下一步：OpenClaw自动注入集成

---

### [decision] 2026-02-12 12:05
v1.2.0 完成总结：1)废话前置过滤器(is_noise) 2)inject命令 3)QMD集成(qmd_search/export-qmd)。router_search现在优先使用QMD检索。下一步：OpenClaw自动注入集成

---


---

## 2026-02-12: 白天轻量检查方案确定

### 背景
- 当前 consolidation 只在凌晨 3 点运行，重要信息延迟捕获
- 参考竞品"三层Cron系统"的 Hourly Micro-Sync 思路
- 需要平衡"实时性"和"质量保证"

### 讨论过程

**最初方案**：检测到重要信息直接 inject 到 Layer 1
- ❌ 被否决：太鲁莽，跳过筛选和去重，可能注入垃圾

**最终方案**：Pending Buffer + Mini-Consolidate

### 最终架构

```
add → 重要性检测 → urgent 标记 → pending.jsonl
                              ↓
白天 mini-consolidate（每3小时）→ 优先处理 pending → 筛选 → 提取 → inject
```

### 待实现组件

| 组件 | 说明 | 状态 |
|------|------|------|
| `pending.jsonl` | 待审池，存放 urgent 记忆 | 待实现 |
| `add` 改造 | 检测重要性，高分写入 pending | 待实现 |
| `mini-consolidate` | 新命令，只处理 pending，跳过衰减 | 待实现 |
| cron 配置 | 白天 5 个时间点触发 | 待实现 |

### 待确认细节

1. **重要性阈值**：importance > 0.8 算 urgent？还是用关键词规则？
2. **mini-consolidate 范围**：只处理 pending，还是 pending + 最近 3 小时普通记忆？
3. **白天时间点**：10点、13点、16点、19点、22点（UTC+8）？

### 设计原则

- 不直接 inject，保证质量
- urgent 记忆优先处理，但仍走筛选流程
- 最坏延迟 3 小时，可接受

---
*记录时间: 2026-02-12 04:28 UTC*
*参与者: Ktao, Tkao*

---

## 2026-02-12: QMD 集成方案细化（Crabby 建议采纳）

### 背景
基于 Crabby 的实战经验反馈，对 QMD 可选增强方案进行补充完善。

### 采纳的建议

#### 1. .gitignore 保护
```bash
# memory/.gitignore
.qmd/
```
防止用户 git 仓库因索引文件爆炸。

#### 2. 空闲时间触发
- 用户 10 分钟没说话 → 后台增量更新索引
- 与 mini-consolidate 的"冷淡期"逻辑一致

#### 3. 索引健康校验
```
memory/.qmd/
├── index/          # 实际索引文件
├── meta.json       # 版本、记忆数、最后更新时间
└── health.lock     # 写入时创建，完成后删除
```
- `health.lock` 存在 → 上次写入中断 → 静默 fallback 到 LLM

#### 4. Hot Store（热存储）
与 `pending.jsonl` 合并，搜索时优先查询未索引的新记忆。

### 最终方案汇总

**目录结构**：
| 组件 | 说明 |
|------|------|
| `memory/.qmd/` | 索引目录，.gitignore 忽略 |
| `meta.json` | 版本、健康状态、最后更新 |
| `health.lock` | 写入锁，防止脏数据 |
| `pending.jsonl` | 热存储，搜索时优先查 |

**触发时机**：
| 时机 | 动作 |
|------|------|
| consolidation 后 | 全量重建索引 |
| 新增 20 条 | 增量更新 |
| 空闲 10 分钟 | 后台增量更新 |

**搜索顺序**：
| 顺序 | 来源 | 速度 |
|------|------|------|
| 1 | pending（热存储） | 极快 |
| 2 | QMD 索引 | 快 |
| 3 | LLM 兜底 | 慢但可靠 |

### 设计原则
- 先保证活着（LLM 兜底），再追求跑得快（QMD 加速）
- 低耦合、易迁移、高可用

---
*记录时间: 2026-02-12 04:34 UTC*
*来源: Crabby 建议 + Ktao/Tkao 讨论*
