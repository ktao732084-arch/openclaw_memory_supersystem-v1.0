# TOOLS.md - Local Notes

Skills define *how* tools work. This file is for *your* specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:
- Camera names and locations
- SSH hosts and aliases  
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras
- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH
- home-server → 192.168.1.100, user: admin

### TTS
- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## 🤖 新增技能（2026-01-29）

### Skill Orchestrator (技能编排器)
- **用途**: 智能技能编排协调器，根据任务复杂度自动路由到最优技能
- **路径**: `/Users/k/moltbot-source/skills/skill-orchestrator`
- **触发条件**: 多技能任务、复杂工作流、模糊请求
- **关键脚本**:
  - `router.py`: 路由决策引擎
  - `skill_matcher.py`: 技能匹配引擎
  - `progress_tracker.py`: 进度跟踪器

### Skill Optimizer (技能优化器)
- **用途**: 一键优化现有Skill的结构和内容组织
- **路径**: `/Users/k/moltbot-source/skills/skill-optimizer`
- **触发条件**: 优化Skill、上传.skill文件
- **关键脚本**:
  - `analyze_skill.py`: 分析Skill结构
  - `optimize_skill.py`: 优化Skill内容
  - `test_skill.py`: 测试优化后的Skill

### Skill Curator (技能策展器)
- **用途**: 智能技能发现和管理系统
- **路径**: `/Users/k/moltbot-source/skills/skill-curator`
- **触发条件**: 需要找技能、扩展能力、搜索AI组件
- **核心理念**: "站在巨人的肩膀上" - 优先使用经过验证的技能

### Test Skill (数据处理技能)
- **用途**: 数据处理和报告生成能力
- **路径**: `/Users/k/moltbot-source/skills/test-skill`
- **触发条件**: 处理数据文件、生成报告、API调用
- **支持格式**: CSV、JSON、TXT
- **输出格式**: HTML、JSON、TXT
- **配置文件**: `assets/config.json`

---

Add whatever helps you do your job. This is your cheat sheet.
