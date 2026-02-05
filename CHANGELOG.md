# Changelog

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
