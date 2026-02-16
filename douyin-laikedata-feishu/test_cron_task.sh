#!/bin/bash
# 测试定时任务执行脚本

echo "=========================================="
echo "测试定时任务执行"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 切换到项目目录
cd /root/.openclaw/workspace/douyin-laikedata-feishu

# 执行同步脚本
echo ""
echo "执行 sync_stable.py..."
python3 sync_stable.py

# 检查退出码
EXIT_CODE=$?
echo ""
echo "=========================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ 测试成功！退出码: $EXIT_CODE"
else
    echo "❌ 测试失败！退出码: $EXIT_CODE"
fi
echo "=========================================="

exit $EXIT_CODE
