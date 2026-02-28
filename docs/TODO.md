# Memory System v1.3.0 - 下一步任务清单

## 🎯 Phase 2: 性能与时序优化

**总工作量**: 45-60 小时  
**优先级**: P1  
**目标**: 提升 LongMemEval 和 LoCoMo 得分

---

## 📋 任务 2.1: 时序查询引擎（15-20h）

### 核心功能

1. **时间谓词重写**
   - [ ] 实现 `TemporalQueryRewriter` 类
   - [ ] 支持相对时间（"上周"、"三个月前"）
   - [ ] 支持绝对时间（"2026年1月"）
   - [ ] 支持时间范围（"去年夏天"）

2. **时间衰减函数**
   - [ ] 实现 `DecayCalculator` 类（已有基础版本）
   - [ ] 支持动态衰减率
   - [ ] 支持重要性影响衰减
   - [ ] 支持访问频率影响衰减

3. **时间跳跃查询**
   - [ ] 实现 `TimeLeapQuery` 类
   - [ ] 支持"三个月前的状态"查询
   - [ ] 支持时间点快照
   - [ ] 支持时间范围聚合

### 实现步骤

**Step 1**: 时间谓词重写（5h）
```python
class TemporalQueryRewriter:
    def rewrite(self, query: str, current_time: datetime) -> Dict:
        """
        重写时序查询
        
        Examples:
            "他上次说的话" → {"time_range": ["2026-02-13", "2026-02-14"]}
            "三个月前" → {"time_range": ["2025-11-14", "2025-11-14"]}
        """
        pass
```

**Step 2**: 时间衰减函数（5h）
```python
class DecayCalculator:
    def calculate_dynamic_score(self, memory: Dict, at_time: datetime = None) -> float:
        """动态计算衰减后的分数"""
        pass
```

**Step 3**: 时间跳跃查询（5h）
```python
class TimeLeapQuery:
    def query_at_time(self, entity: str, attribute: str, at_time: datetime) -> Any:
        """查询指定时间点的属性值"""
        pass
```

**Step 4**: 集成测试（5h）
- 单元测试
- 集成测试
- LongMemEval 子集测试

### 成功指标

- [ ] 时序查询准确率 > 75%
- [ ] LongMemEval 得分提升至 70-80%
- [ ] 测试覆盖 > 90%

---

## 📋 任务 2.2: 事实演变追踪（20-25h）

### 核心功能

1. **实体属性演变历史**
   - [ ] 实现 `FactEvolutionTracker` 类
   - [ ] 追踪属性变化历史
   - [ ] 维护有效期（valid_from, valid_to）
   - [ ] 支持多属性追踪

2. **知识失效检测**
   - [ ] 实现 `KnowledgeInvalidator` 类
   - [ ] 自动识别过时信息
   - [ ] 标记失效记忆
   - [ ] 触发更新通知

3. **当前值查询**
   - [ ] 实现 `CurrentValueQuery` 类
   - [ ] 查询指定时间点的属性值
   - [ ] 支持"用户现在住在哪里"
   - [ ] 支持属性历史查询

### 实现步骤

**Step 1**: 实体属性演变历史（8h）
```python
class FactEvolutionTracker:
    def track_evolution(self, entity: str, attribute: str) -> List[Dict]:
        """
        追踪实体属性的演变历史
        
        Returns:
            [
                {"value": "北京", "valid_from": "2025-01-01", "valid_to": "2026-01-01"},
                {"value": "上海", "valid_from": "2026-01-01", "valid_to": None}
            ]
        """
        pass
```

**Step 2**: 知识失效检测（8h）
```python
class KnowledgeInvalidator:
    def detect_invalidation(self, new_memory: Dict, old_memories: List[Dict]) -> List[str]:
        """检测哪些旧记忆被新记忆失效"""
        pass
```

**Step 3**: 当前值查询（4h）
```python
class CurrentValueQuery:
    def get_current_value(self, entity: str, attribute: str, at_time: datetime = None) -> Any:
        """获取指定时间点的属性值"""
        pass
```

**Step 4**: 集成测试（5h）
- 单元测试
- 演变场景测试
- LongMemEval 测试

### 成功指标

- [ ] 事实演变追踪准确率 > 80%
- [ ] 知识失效检测准确率 > 85%
- [ ] LongMemEval 得分提升至 75-85%

---

## 📋 任务 2.3: 证据追踪（10-15h）

### 核心功能

1. **证据链构建**
   - [ ] 实现 `EvidenceTracker` 类
   - [ ] 追踪记忆的来源链
   - [ ] 支持多跳证据追踪
   - [ ] 构建证据图

2. **LoCoMo 格式输出**
   - [ ] 实现 `LoCoMoFormatter` 类
   - [ ] 返回 evidence_ids
   - [ ] 返回 session_id
   - [ ] 返回 confidence

3. **证据溯源**
   - [ ] 实现 `EvidenceTracer` 类
   - [ ] 从记忆追溯到原始对话
   - [ ] 支持"为什么这么说"
   - [ ] 生成证据解释

### 实现步骤

**Step 1**: 证据链构建（5h）
```python
class EvidenceTracker:
    def get_evidence_chain(self, memory_id: str) -> List[Dict]:
        """获取证据链"""
        pass
```

**Step 2**: LoCoMo 格式输出（3h）
```python
class LoCoMoFormatter:
    def format_for_locomo(self, memory: Dict) -> Dict:
        """格式化为 LoCoMo 要求的输出"""
        return {
            'answer': memory['content'],
            'evidence_ids': [...],
            'confidence': memory['confidence']
        }
```

**Step 3**: 证据溯源（4h）
```python
class EvidenceTracer:
    def trace_to_source(self, memory_id: str) -> Dict:
        """追溯到原始对话"""
        pass
```

**Step 4**: 集成测试（3h）
- 单元测试
- LoCoMo 格式测试
- 端到端测试

### 成功指标

- [ ] 证据溯源完整性 100%
- [ ] LoCoMo 格式正确率 100%
- [ ] LoCoMo 得分提升至 70-80%

---

## 🔧 技术准备

### 开发环境

- [ ] Python 3.11+
- [ ] SQLite 3.35+
- [ ] pytest（测试框架）
- [ ] 评测集数据（需要下载）

### 依赖库

```bash
# 可能需要的新依赖
pip install sentence-transformers  # 语义相似度（可选）
pip install dateparser              # 时间解析
pip install python-dateutil         # 时间处理
```

### 数据准备

- [ ] 下载 LongMemEval 数据集
- [ ] 下载 LoCoMo 数据集
- [ ] 准备测试数据（1000+ 条记忆）

---

## 📅 时间规划

### Week 1（本周）

**目标**: 完成 Phase 2.1

- Day 1-2: 时间谓词重写（5h）
- Day 3-4: 时间衰减函数（5h）
- Day 5-6: 时间跳跃查询（5h）
- Day 7: 集成测试（5h）

### Week 2（下周）

**目标**: 完成 Phase 2.2

- Day 1-3: 实体属性演变历史（8h）
- Day 4-6: 知识失效检测（8h）
- Day 7: 当前值查询 + 测试（9h）

### Week 3（第三周）

**目标**: 完成 Phase 2.3

- Day 1-2: 证据链构建（5h）
- Day 3: LoCoMo 格式输出（3h）
- Day 4-5: 证据溯源（4h）
- Day 6-7: 集成测试 + 优化（3h）

---

## 🎯 验收标准

### Phase 2 完成标准

- [ ] 所有任务的测试覆盖 > 90%
- [ ] LongMemEval 得分 > 70%
- [ ] LoCoMo 得分 > 70%
- [ ] 代码审查通过
- [ ] 文档完整

### 性能标准

- [ ] 时序查询延迟 < 100ms
- [ ] 演变追踪延迟 < 50ms
- [ ] 证据追踪延迟 < 50ms
- [ ] 内存占用 < 500MB（10000 条记忆）

---

## 📞 需要帮助？

如果在开发过程中遇到问题：

1. 查看 [PROGRESS.md](PROGRESS.md) 了解当前进度
2. 查看 [v1.3.0-development-plan.md](docs/v1.3.0-development-plan.md) 了解整体规划
3. 查看 [benchmark-research-report.md](docs/benchmark-research-report.md) 了解评测集要求

---

**文档版本**: v1.0  
**创建时间**: 2026-02-14 05:06 UTC  
**维护者**: [助手]
