# Changelog

本项目的所有重要变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [v1.5.2] - 2026-02-21

### 🔧 Hotfix - 暂时禁用 OpenClaw 集成

#### 🚫 暂时禁用功能
- **禁用**: `openclaw_bridge.py` - WebSocket 实时桥接（重命名为 `.disabled`）
- **禁用**: `openclaw_config_sync.py` - 配置同步工具（重命名为 `.disabled`）
- **移除**: AGENTS.md 中的 Layer 1 自动注入块

#### ⚠️ 原因说明
- OpenClaw Gateway 在配置了监听功能后无法启动
- 等待官方优化后再重新启用

#### 📝 恢复说明
- 未来需要恢复时，将 `.disabled` 后缀去掉即可
- Layer 1 注入块可以通过 `openclaw_config_sync.py sync-layer1` 重新生成

---

## [v1.5.1] - 2026-02-20

### ✨ Feature - OpenClaw 集成完善

#### 🔗 配置同步工具
- **新增**: `openclaw_config_sync.py` 自动配置工具
  - `sync-layer1`: Layer 1 自动注入配置
  - `setup-cron`: 定时 Consolidation 配置
  - `setup-bridge`: Bridge 自动启动配置
  - `full-sync`: 完整配置同步

#### 🔄 断线重连优化
- **改进**: 指数退避策略，最大 5 次重试
- **改进**: 心跳保活机制（30s 间隔）

#### 📝 文档更新
- **新增**: OpenClaw 集成快速开始指南
- **新增**: 配置说明和示例

---

## [v1.5.0] - 2026-02-18

### ✨ Feature - 向量检索集成

#### 🧠 向量嵌入引擎
- **新增**: 多嵌入提供者支持
  - OpenAI: `text-embedding-3-small` / `text-embedding-3-large`
  - HuggingFace: `all-MiniLM-L6-v2` / `all-mpnet-base-v2`
  - 本地模型: `sentence-transformers`
- **新增**: 嵌入缓存机制，减少 API 调用

#### 📦 向量索引模块
- **新增**: SQLite 向量存储后端（默认）
- **新增**: Qdrant 向量存储后端（高级）
- **新增**: 向量 CRUD 操作

#### 🔍 混合检索引擎
- **新增**: 关键词 + 向量权重融合
- **新增**: 可配置权重（默认: 关键词 0.3, 向量 0.7）
- **新增**: 最小分数阈值过滤

#### 🛠️ CLI 命令
- `vector-build`: 构建向量索引
- `vector-search`: 向量检索
- `vector-status`: 查看索引状态
- `vector-config`: 配置参数

#### ⚙️ 配置项
```json
{
  "vector": {
    "enabled": false,
    "provider": "openai",
    "model": "text-embedding-3-small",
    "dimension": 1536,
    "backend": "sqlite",
    "hybrid_search": {
      "keyword_weight": 0.3,
      "vector_weight": 0.7,
      "min_score": 0.2
    }
  }
}
```

---

## [v1.4.0] - 2026-02-15

### ✨ Feature - 百万级扩展支持

#### 📊 分片索引管理器
- **新增**: 自动分片，每分片最多 10,000 条记录
- **新增**: 并行检索所有分片
- **新增**: 分片统计和监控

#### 💾 多级缓存系统
- **新增**: L1 缓存（热点记忆，TTL 1小时）
- **新增**: L2 缓存（查询结果，TTL 5分钟）
- **新增**: L3 缓存（嵌入向量，TTL 24小时）

#### ⚡ 异步索引器
- **新增**: 后台批量处理
- **新增**: 优先级队列
- **新增**: 批量索引更新

#### 🗄️ 向量数据库适配器
- **新增**: Qdrant 适配器
- **新增**: Pinecone 适配器（计划中）

#### 📈 性能目标
| 指标 | 目标 |
|------|------|
| 记忆容量 | 1,000,000+ |
| 检索延迟 | <100ms |
| 缓存命中率 | >80% |
| 索引吞吐 | >1000/s |

---

## [v1.3.0] - 2026-02-10

### ✨ Feature - OpenClaw Gateway 深度集成

#### 🌐 WebSocket 实时桥接
- **新增**: `openclaw_bridge.py` 桥接模块
- **新增**: 实时消息监听与捕获
- **新增**: 自动添加到 pending buffer

#### 💉 动态记忆注入
- **新增**: 触发关键词检测
- **新增**: 检索相关记忆并注入到会话
- **新增**: Urgent 检测与 mini-consolidate 触发

#### 🔧 配置同步
- **新增**: Layer 1 自动注入配置
- **新增**: Cron 定时 Consolidation 配置
- **新增**: Bridge 自动启动配置

#### ⚙️ 配置项
```json
{
  "openclaw": {
    "enabled": true,
    "gateway_url": "ws://127.0.0.1:18789",
    "auto_inject": true,
    "inject_threshold": 0.6,
    "trigger_keywords": ["之前", "上次", "以前", "还记得", "我记得"]
  }
}
```

---

## [v1.2.0] - 2026-02-07

### 🐛 Bug Fixes - 稳定性优化

#### 💾 IO 竞态修复
- **修复**: 切换到 SQLite 后端，解决 JSONL 文件并发写入问题
- **修复**: 添加文件锁机制

#### 🚀 冷启动优化
- **改进**: 模块合并，减少导入时间
- **改进**: 延迟加载大型依赖

#### 📈 增量索引更新
- **改进**: 只更新变化的索引项
- **改进**: 减少全量重建频率

#### 🎯 整合期实体抑制
- **修复**: Consolidation 期间避免实体重复提取

---

## [v1.1.7] - 2026-02-06

### 🧠 Feature - LLM 深度集成

#### 🔍 语义复杂度检测（新增）
- **问题**: 规则引擎太"自信"，大部分内容都被规则接住，LLM 形同虚设
- **解决**: 新增语义复杂度检测，识别需要 LLM 处理的复杂内容
- **检测维度**:
  - 关系指示词（认为、觉得、怀疑、可能...）
  - 否定/反转词（不是、其实、实际上...）
  - 隐喻/比喻词（像、如同、仿佛...）
  - 时间复杂性（之前、之后、同时...）
  - 多实体检测
  - 句子结构复杂度

#### ⚡ 扩大 LLM 触发区间
- **原逻辑**: 只有 0.2~0.3 才触发 LLM（太窄）
- **新逻辑**: 
  - 高置信度（>0.5）+ 简单内容 → 信任规则
  - 高置信度（>0.5）+ 复杂内容 → 强制 LLM
  - 不确定区间（0.2~0.5）→ 使用 LLM
  - 低置信度（<0.2）+ 复杂内容 → 使用 LLM
  - 低置信度（<0.2）+ 简单内容 → 丢弃

#### 🔄 LLM 失败回退机制
- **问题**: LLM 调用失败时静默丢弃信息
- **解决**: 失败时回退到规则结果，不丢弃
- **效果**: 即使 API Key 缺失或网络问题，也能保留记忆

#### 🔑 API Key 多源获取
- **优先级**: 参数传入 > 环境变量 > 配置文件
- **环境变量**: `OPENAI_API_KEY`
- **配置文件**: `llm_api_key` 字段

### 📊 新增模块
- **`v1_1_7_llm_integration.py`** (18 KB)
  - `detect_semantic_complexity()`: 语义复杂度检测
  - `should_use_llm_for_filtering()`: LLM 触发决策
  - `smart_filter_segment()`: 智能筛选
  - `smart_extract_entities()`: 智能实体提取
  - `call_llm_with_fallback()`: 带回退的 LLM 调用
  - `LLMIntegrationStats`: 统计追踪

### 📊 测试结果
- v1.1.7 新增测试: 29/29 通过
- v1.1.6 原有测试: 17/17 通过
- v1.1.5 原有测试: 8/8 通过

### 🙏 致谢
感谢 Crabby 的深度测试和犀利评价：
- 指出 LLM 兜底机制"形同虚设"
- 指出规则引擎"伪智能的枷锁"
- 指出 LLM 失败时"静默丢弃"的危险

---

## [v1.1.6] - 2026-02-06

### 🐛 Bug Fixes - Crabby 测试反馈修复

#### 🔤 引号实体提取（P0）
- **问题**: 实体提取的"合并性坍塌"，`'寒武纪'项目` 只提取到"项目"
- **修复**: 新增 Layer 0 引号实体提取，优先级最高
- **支持引号**: `「」` `『』` `""` `''` `《》` `''` `""`
- **效果**: `张三负责'寒武纪'项目` → `['寒武纪', '项目']`

#### 📊 去重阈值改用相对比例（P0）
- **问题**: 长句中 `overlap > 3` 太松，导致"多包并存"
- **修复**: 改用相对比例 `overlap_ratio >= 0.3`（30%）
- **效果**: 短句（10词）3词重叠=30%去重，长句（50词）3词重叠=6%不去重

#### 🔀 分层冲突信号（P1）
- **问题**: "逗你的"、"开玩笑"等口语修正信号未被识别
- **修复**: 分层冲突信号
  - **Tier 1**（强降权 10%）: "其实是"、"实际上"、"更正"等
  - **Tier 2**（弱降权 40%）: "逗你的"、"开玩笑"、"骗你的"等
- **效果**: 花生过敏场景正确处理，旧记忆被 Tier 2 降权

#### 🀄 中文分词优化
- **问题**: `split()` 对中文无效，导致重叠计算错误
- **修复**: 新增 `tokenize_chinese()` 函数，使用字符级 2-gram + 英文单词
- **效果**: 中文短句去重正确工作

### 📊 测试结果
- v1.1.6 新增测试: 17/17 通过
- v1.1.5 原有测试: 8/8 通过

### 🙏 致谢
感谢 Crabby 的深度测试，发现了：
1. 引号实体的"合并性坍塌"问题
2. 去重阈值的"长句失效"问题
3. 口语修正信号的"识别盲区"问题

---

## [v1.1.5] - 2026-02-06

### ✨ Feature - 实体识别与隔离系统

#### 🧠 三层实体识别（集成到 `extract_entities` 函数）
- **Layer 1**: 硬编码模式（ENTITY_PATTERNS，0 Token）
- **Layer 2**: 学习过的实体（learned_entities.json，0 Token）
- **Layer 3**: LLM 提取 + 自动学习（仅首次调用）
- **集成位置**: 修改原有 `extract_entities()` 函数，保持向后兼容

#### ⚡ 竞争性抑制（集成到 `rerank_results` 函数）
- 解决相似实体混淆问题（如 "机器人_50" vs "机器人_5"）
- 精确匹配保持原权重，相似但不同的实体断崖降权（× 0.1）
- **集成位置**: 修改原有 `rerank_results()` 函数，在排序逻辑中应用

#### 📈 访问加成修复（修改 `v1_1_helpers.calculate_access_boost`）
- 使用"最近 N 天"替代"总天数"
- 老记忆被重新激活后能快速"复活"
- **集成位置**: 直接修改 `v1_1_helpers.py` 中的原函数

#### 🗑️ 学习实体清理（在 Phase 5 执行）
- 在 Consolidation Phase 5 自动清理废弃实体
- 一年未使用的实体自动删除
- **集成位置**: `cmd_consolidate` Phase 5 中调用

### 🔧 架构改进
- **正确集成**: 修改原有函数而非绕过
- **向后兼容**: 新参数有默认值，不影响原有调用
- **优雅降级**: V1_1_5_ENABLED 为 False 时自动回退到原有逻辑

### 📊 测试结果
- 8/8 测试通过

---

## [v1.1.4] - 2026-02-05

### ✨ Feature - 访问追踪与时间敏感

#### 📊 访问日志追踪
- **新增**: 记录每次记忆被访问的时间
- **新增**: 访问次数统计
- **改进**: 基于访问频率调整记忆权重

#### ⏰ 时间敏感记忆
- **新增**: 自动识别和清理过期信息
- **新增**: 时间范围过滤
- **改进**: 过期记忆自动降权

---

## [v1.1.3] - 2026-02-05

### ✨ Feature - LLM 兜底机制

- **规则优先，LLM 兜底**: 实现完整的混合动力架构
  - Phase 2 (筛选): 规则无法判断时（阈值附近 ±0.1），自动调用 LLM
  - Phase 3 (提取): 实体为空时，自动调用 LLM 提取
  - 使用用户的 API Key（从 `os.environ` 读取 `OPENAI_API_KEY`）
  - 支持自定义模型（`MEMORY_LLM_MODEL` 环境变量）
  - 支持自定义 Base URL（`OPENAI_BASE_URL` 环境变量）

### 📊 Monitoring
- **LLM 调用统计**: Consolidation 结束时显示
  - Phase 2/3 调用次数
  - 总 Token 消耗
  - 错误次数
  - 纯规则处理时显示"Token 节省: 100%"

### 🔧 Configuration
- 新增配置项：
  ```json
  "llm_fallback": {
    "enabled": true,
    "phase2_filter": true,
    "phase3_extract": true,
    "phase4b_verify": false,
    "min_confidence": 0.6
  }
  ```

### 🎯 Token 节省效果
- 简单场景（规则可处理）: 100% 节省（0 Token）
- 复杂场景（需要 LLM）: 仅在必要时调用，节省 ~90%

### 📝 环境变量
- `OPENAI_API_KEY`: OpenAI API Key（必需，如果启用 LLM）
- `OPENAI_BASE_URL`: API Base URL（可选，默认 OpenAI 官方）
- `MEMORY_LLM_MODEL`: 模型名称（可选，默认 gpt-3.5-turbo）
- `MEMORY_LLM_ENABLED`: 是否启用 LLM（可选，默认 true）

---

## [v1.1.2] - 2026-02-05

### 🔧 Hotfix - 实体识别优化

- **实体识别优化**: 支持正则模式匹配动态实体
  - 新增 `patterns` 字段，支持正则表达式
  - 可识别 `城市_1`、`项目_25`、`Memory-System` 等动态实体
  - 优化匹配逻辑，优先保留长实体（避免 `Memory-System` 被拆成 `Memory` 和 `System`）
  - 解决 Crabby 极压测试中发现的"50个城市实体全部变成无主记忆"问题

### 🐛 Bug Fixes
- 修复实体识别只能匹配固定列表的问题
- 修复子串实体重复匹配问题（如 `Memory` 和 `Memory-System` 同时出现）

### 📊 Performance
- 实体识别精度提升 ~30%（动态实体场景）
- 检索准确性提升（实体关联更完整）

---

## [v1.1.1] - 2026-02-05

### 🔧 Hotfix - 分词优化

- **分词优化**: 改进 `extract_keywords` 函数，保留连字符词（如 `memory-system`, `v1.1`, `API-key`）
  - 优先提取英文/数字连字词
  - 改进中文词组提取（2字以上）
  - 提取纯英文单词（不含连字符）
  - 解决了技术词汇被拆分导致检索精度下降的问题

### ✨ Feature - 冲突柔性降权
- **冲突柔性降权**: 新增记忆冲突检测机制
  - 添加 `OVERRIDE_SIGNALS` 列表（"不再"、"改成"、"搬到"等覆盖性关键词）
  - 在 Phase 4a 去重时，检测新记忆是否包含覆盖信号
  - 对冲突的旧记忆执行惩罚性降权（score *= 0.2）
  - 保留历史记忆，但通过降权确保 Agent 优先使用新信息
  - 添加 `conflict_downgraded` 标记和 `downgrade_reason` 字段

### 📊 Stability - 指标透明化
- **指标透明化**: Layer 1 快照中新增"已降权记忆"部分
  - 使用 📉 标记和删除线显示被降权的记忆
  - 显示降权前后的 Score 变化
  - 帮助用户理解记忆系统的冲突处理逻辑

### 🔧 Configuration
- 版本号更新至 `1.1.1`
- 新增配置项：
  ```json
  "conflict_detection": {
    "enabled": true,
    "penalty": 0.2
  }
  ```

### 🐛 Bug Fixes
- 修复 `deduplicate_facts` 返回值不一致问题（现在返回 3 个值）
- 修复降权记忆未持久化的问题（现在会重写 facts.jsonl）

---

## [v1.1.0] - 2026-02-05

### ✨ Features
- 完整实现 Router 检索系统
- 完整实现 Consolidation 流程（Phase 1-7）
- 新增 `search` 命令
- 改进中文分词

### 📈 Performance
- 实现率从 ~35% 提升至 ~95%

---

## [v1.0.0] - 2026-02-04

### 🎉 Initial Release
- 三层记忆架构设计
- 基础 CLI 工具
- Phase 2-4 核心逻辑
- 衰减机制
- 实体档案系统

---

## 版本号说明

本项目遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)：

- **MAJOR（主版本号）**: 不兼容的 API 变更
- **MINOR（次版本号）**: 向后兼容的功能新增
- **PATCH（修订号）**: 向后兼容的问题修复
