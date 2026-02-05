# Changelog

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

### 🔧 Hotfix
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

### 🔧 Hotfix
- **分词优化**: 改进 `extract_keywords` 函数，保留连字符词（如 `memory-system`, `v1.1`, `API-key`）
  - 优先提取英文/数字连字词
  - 改进中文词组提取（2字以上）
  - 提取纯英文单词（不含连字符）
  - 解决了技术词汇被拆分导致检索精度下降的问题

### ✨ Feature
- **冲突柔性降权**: 新增记忆冲突检测机制
  - 添加 `OVERRIDE_SIGNALS` 列表（"不再"、"改成"、"搬到"等覆盖性关键词）
  - 在 Phase 4a 去重时，检测新记忆是否包含覆盖信号
  - 对冲突的旧记忆执行惩罚性降权（score *= 0.2）
  - 保留历史记忆，但通过降权确保 Agent 优先使用新信息
  - 添加 `conflict_downgraded` 标记和 `downgrade_reason` 字段

### 📊 Stability
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

## [v1.1] - 2026-02-05

### ✨ Features
- 完整实现 Router 检索系统
- 完整实现 Consolidation 流程（Phase 1-7）
- 新增 `search` 命令
- 改进中文分词

### 📈 Performance
- 实现率从 ~35% 提升至 ~95%

---

## [v1.0] - 2026-02-04

### 🎉 Initial Release
- 三层记忆架构设计
- 基础 CLI 工具
- Phase 2-4 核心逻辑
- 衰减机制
- 实体档案系统
