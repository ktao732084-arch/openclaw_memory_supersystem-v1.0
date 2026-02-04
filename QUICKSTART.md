# 快速开始指南 - Tkao Memory System MVP

## 🚀 5分钟上手

### 1. 测试社交追踪器

```bash
cd /root/.openclaw
python3 skills/moltbook-social-tracker/main.py
```

**预期输出**:
```
Testing Moltbook Social Tracker...

1. Tracking agent interaction...
   Task ID: xxx

2. Tracking post creation...
   Task ID: xxx

✓ All tests completed!
```

### 2. 查看Layer 3事件日志

```bash
cat /root/.openclaw/workspace/memory/layer3/2026-02-03.jsonl | jq
```

### 3. 生成Layer 1快照

```bash
cd /root/.openclaw
python3 memory/snapshot_generator.py
```

**查看快照**:
```bash
cat /root/.openclaw/workspace/memory/snapshot.md
```

### 4. 运行完整测试

```bash
cd /root/.openclaw
python3 memory/test_mvp.py
```

---

## 📝 在OpenClaw中使用

### 方式1: 直接调用Python

```python
# 在你的agent代码中
import sys
sys.path.insert(0, '/root/.openclaw/skills/moltbook-social-tracker')
from main import MoltbookSocialTracker

tracker = MoltbookSocialTracker()

# 当Moltbook社交活动发生时
tracker.track_agent_interaction(
    agent_name="Shellraiser",
    interaction_type="reply",
    topic="经济系统讨论",
    quality_score=4.5
)
```

### 方式2: 通过Skill系统（待实现）

```yaml
# .openclaw/config.json
{
  "skills": {
    "moltbook-social-tracker": {
      "enabled": true,
      "auto_track": true
    }
  }
}
```

---

## 🔄 手动Consolidation（临时方案）

在Consolidation Skill完成前，你可以手动运行：

```bash
# 1. 追踪今天的活动
python3 skills/moltbook-social-tracker/main.py

# 2. 生成快照
python3 memory/snapshot_generator.py

# 3. 查看结果
cat workspace/memory/snapshot.md
```

---

## 📊 当前状态

| 组件 | 状态 | 说明 |
|------|------|------|
| SOUL.md | ✅ 完成 | 身份定义和规则 |
| Domain配置 | ✅ 完成 | 3个域配置 |
| Social Tracker | ✅ 完成 | 追踪社交活动 |
| Ranking Calculator | ✅ 完成 | 计算排名分数 |
| Snapshot Generator | ✅ 完成 | 生成Layer 1快照 |
| Consolidation Skill | ❌ 待实现 | 连接Layer 3→2→1 |
| Memory Router | ❌ 待实现 | 按需召回记忆 |

---

## 🎯 下一步

1. **实现Consolidation Skill** - 自动化Layer 3→2→1流程
2. **集成Memory Router** - 按需召回记忆
3. **完整测试** - 端到端测试

---

## 💡 提示

- Layer 3事件日志已经正常工作
- 可以手动创建Layer 2对象来测试快照生成
- 所有测试脚本都可以独立运行
- 查看MVP_COMPLETION_REPORT.md了解完整功能
