# 记忆系统设计项目 - 对话记录与进度

## 项目信息
- **项目名称**: Memory System v1.0
- **开始时间**: 2026-02-03
- **最后更新**: 2026-02-04
- **状态**: ✅ v1.0 完成

---

## 一、已完成的设计模块

### 1. ✅ 架构细化（完成）

#### 1.1 设计原则（已确认）
| 原则 | 定义 |
|------|------|
| 检索优先 | 不是"记得多"，而是"找得准" |
| 可计算 | 所有记忆必须可排序/可打分/可索引 |
| 写复杂读简单 | 复杂逻辑在写入时处理，读取O(1) |
| 自动衰减 | 旧记忆自动降权，不依赖手动清理 |

#### 1.2 三层架构（已确认）
| 层级 | 定位 | Token预算 | 格式 | 更新频率 |
|------|------|----------|------|---------|
| Layer 1 | 工作记忆 | 2000-4000 | Markdown | 每日冷淡期 |
| Layer 2 | 结构化长期记忆 | 不限 | JSONL + JSON | Consolidation时 |
| Layer 3 | 原始事件日志 | 不限 | MD + JSONL | 实时 |

#### 1.3 Layer 1 结构（已确认）
```
1. Identity（~100 tokens）- 固定
2. Owner（~150 tokens）- 固定
3. Constraints（~100 tokens）- 固定
4. Top Summaries（~800-1500 tokens）- 动态，按排名分配
5. Ranked Index（~600-1500 tokens）- 动态，按排名分配
6. Recent（~200 tokens）- 动态
```

**核心设计决策**:
- 排名靠前 → 丰富度高（不是反过来）
- Token分配按排名递减：#1=40%, #2=25%, #3=15%, 其余=20%
- Index分层：高排名（丰富）、中排名（简洁）、低排名（仅指针）

#### 1.4 Layer 2 结构（已确认）
- **memory_class**: fact / belief / summary
- **granularity**: atomic / composite
- **confidence**: 0-1 置信度
- **存储格式**: JSONL（facts.jsonl, beliefs.jsonl, summaries.jsonl）
- **实体档案**: entities/ 目录
- **分池管理**: active/（活跃池）+ archive/（归档池）

#### 1.5 Layer 3 结构（已确认）
- **双格式**: YYYY-MM-DD.md（人类可读）+ YYYY-MM-DD.jsonl（机器处理）
- **事件类型**: input, output, action, result, decision, error
- **原则**: 只记录事实，不推断，只追加不修改

#### 1.6 排名权重系统（已确认）
```python
排名分数 = 基础权重 × 时间衰减 + 访问频率加成 + 重要性加成
```

#### 1.7 衰减率（已确认）
| 类型 | 衰减率 | 半衰期 |
|------|--------|--------|
| fact | 0.008 | ~87天 |
| belief | 0.07 | ~10天 |
| summary | 0.025 | ~28天 |
| event | 0.15 | ~5天 |

#### 1.8 更新机制（已确认）
- **冷淡期定义**: 20分钟无消息 + 非活跃时段 + 无对话
- **更新频率**: 每日一次，冷淡期触发

---

### 2. ✅ Router 逻辑（完成）

#### 2.1 触发条件体系（已确认）
| 层级 | 触发条件 | 成本 |
|------|---------|------|
| Layer 0 | 显式请求、时间引用 | O(1) |
| Layer 1 | 大事件命中、关键词匹配 | O(n) |
| Layer 2 | 任务类型映射 | O(1) |
| Layer 3 | 语义匹配（仅兜底） | O(n) |

#### 2.2 检索策略（已确认）
- **核心**: 检索宽，注入窄
- **数量配置**:
  - 精准查询: 初始12-15 → 重排8-10 → 最终5-8
  - 主题查询: 初始20-25 → 重排13-16 → 最终10-13
  - 广度查询: 初始30-35 → 重排20-25 → 最终15-18

#### 2.3 结果注入（已确认）
- 高置信度(>0.8): 直接注入，无标记
- 中置信度(0.5-0.8): 注入 + 来源标记
- 低置信度(<0.5): 仅提供引用路径

#### 2.4 其他机制（已确认）
- **自评估**: 评估结果充分性，必要时补充检索
- **缓存**: 会话级缓存，TTL 30分钟
- **Token预算**: 动态计算Top-K

---

### 3. ✅ Consolidation 流程（完成）

详见 `consolidation_report_v1.0.md`

---

### 4. ✅ Skill 实现（完成）

#### 4.1 实现内容
- **核心脚本**: `scripts/memory.py` - 完整 CLI 工具
- **Prompt 模板**: Phase 2/3/4/7 的 Prompt 设计
- **配置模板**: 默认配置和快照模板
- **设计文档**: 完整的架构和使用说明

#### 4.2 功能清单
| 功能 | 状态 |
|------|------|
| 初始化 (init) | ✅ |
| 记忆添加 (capture) | ✅ |
| 状态查看 (status) | ✅ |
| 统计信息 (stats) | ✅ |
| Consolidation | ✅ |
| 手动归档 (archive) | ✅ |
| 索引重建 (rebuild-index) | ✅ |
| 数据验证 (validate) | ✅ |
| 输入验证 | ✅ |
| Layer 1 增强快照 | ✅ |

#### 4.3 性能指标
| 指标 | 结果 |
|------|------|
| 单条记忆添加 | ~39ms |
| Consolidation (100条) | ~51ms |
| 单次衰减 (100条) | ~43ms |
| 存储空间 (100条) | 64KB |
| Layer 1 快照 | ~690 tokens |

#### 4.4 测试覆盖
- ✅ 初始化功能
- ✅ 记忆添加（fact/belief/summary）
- ✅ 输入验证（空内容、范围检查）
- ✅ Consolidation 完整流程
- ✅ Consolidation 单独 Phase
- ✅ 衰减机制（30/90/180 天模拟）
- ✅ 归档机制（自动/手动）
- ✅ 索引系统
- ✅ Layer 1 快照生成
- ✅ 数据完整性验证
- ✅ 性能压力测试（100 条记忆）
- ✅ 边界情况处理

---

## 二、文件结构

### 2.1 Skill 文件结构
```
memory-system-skill/
├── README.md                    # 简介
├── LICENSE                      # MIT 许可证
├── SKILL.md                     # 完整使用文档
├── scripts/
│   └── memory.py                # 核心 CLI 脚本
├── prompts/
│   ├── filter.md                # Phase 2 筛选
│   ├── extract.md               # Phase 3 提取
│   ├── verify_belief.md         # Phase 4b 验证
│   ├── generate_summary.md      # Phase 4c 摘要
│   └── snapshot.md              # Phase 7 快照
├── templates/
│   ├── config.json              # 默认配置
│   └── snapshot.md              # Layer 1 模板
└── docs/
    └── design.md                # 设计文档
```

### 2.2 运行时文件结构
```
memory/
├── config.json                 # 全局配置
├── layer1/
│   └── snapshot.md             # Layer 1 快照
├── layer2/
│   ├── active/                 # 活跃池
│   │   ├── facts.jsonl
│   │   ├── beliefs.jsonl
│   │   └── summaries.jsonl
│   ├── archive/                # 归档池
│   │   ├── facts.jsonl
│   │   ├── beliefs.jsonl
│   │   └── summaries.jsonl
│   ├── entities/               # 实体档案
│   │   ├── _index.json
│   │   └── *.json
│   └── index/                  # 索引
│       ├── keywords.json
│       ├── timeline.json
│       └── relations.json
└── state/
    ├── consolidation.json      # Consolidation 状态
    └── rankings.json           # 排名快照
```

---

## 三、设计报告位置

1. **架构细化报告**: 本文件 第一节
2. **Router 逻辑报告**: 本文件 第二节
3. **Consolidation 报告**: `consolidation_report_v1.0.md`
4. **Skill 完整文档**: `memory-system-skill/SKILL.md`

---

## 四、待完善（后续版本）

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 接入 OpenClaw session 数据 | 高 | Phase 1-3 真实数据源 |
| 时间线索引实现 | 中 | 按时间检索 |
| 关键词分词优化 | 中 | 更精细的关键词提取 |
| Phase 1-3 真实模型调用 | 高 | 完整的提取流程 |
| 访问记录和访问加权 | 低 | v1.1 计划 |
| 归档内容激活机制 | 低 | v1.1 计划 |

---

## 五、关键设计理念

1. **Layer 1 不是"最重要的记忆"，而是"每次对话都需要的记忆"**
2. **排名靠前 → 丰富度高（不是反过来）**
3. **结构化优于叙述：大模型更擅长处理结构化数据**
4. **检索宽，注入窄：多检索候选，精筛选注入**
5. **精确优先，语义兜底：低成本规则先行，高成本语义后备**
6. **不影响用户体验：所有后台操作都在冷淡期或用最小功耗执行**
7. **重要性由语义决定，不依赖使用频率**
8. **分池管理：活跃池参与重算，归档池按需激活**

---

## 六、发布信息

- **版本**: v1.0.0
- **发布日期**: 2026-02-04
- **压缩包**: `/root/memory-system-v1.0.0.zip`
- **许可证**: MIT

---

*此文件用于在新对话中快速恢复上下文，继续记忆系统设计讨论。*
