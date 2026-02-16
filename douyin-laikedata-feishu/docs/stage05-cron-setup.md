# 第五阶段：定时任务

## 完成时间
2026-02-12

## 目标
设置 OpenClaw Cron 定时任务，实现每天自动同步

---

## 实施过程

### 1. OpenClaw Cron 配置
- **任务名称**: "抖音来客数据同步"
- **执行时间**: 每天早上 7:00（北京时间）
- **Cron 表达式**: `0 7 * * *`
- **时区**: `Asia/Shanghai`
- **任务ID**: `0a3447a4-6114-4efb-9bbc-ebd25231df3f`

### 2. 执行脚本
- **主脚本**: `sync_data.py`
- **包装脚本**: `run.sh`
- **下次执行**: 2026-02-13 07:00

### 3. Cron 配置详情
```json
{
  "name": "抖音来客数据同步",
  "schedule": {
    "kind": "cron",
    "expr": "0 7 * * *",
    "tz": "Asia/Shanghai"
  },
  "payload": {
    "kind": "systemEvent",
    "text": "cd /root/.openclaw/workspace/douyin-laikedata-feishu && python3 sync_data.py"
  },
  "sessionTarget": "main",
  "enabled": true
}
```

---

## 核心文件
- `sync_data.py` - 主同步脚本
- `run.sh` - 执行包装脚本

---

*创建时间: 2026-02-12*
