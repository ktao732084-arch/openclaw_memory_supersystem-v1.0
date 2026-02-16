#!/bin/bash
# 抖音来客数据同步任务执行脚本

cd /root/.openclaw/workspace/douyin-laikedata-feishu

echo "=========================================="
echo "抖音来客数据同步任务"
echo "执行时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

python3 sync_data.py

echo ""
echo "任务执行完成"
