#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

REPORT_FILE="$SCRIPT_DIR/health_check_report.txt"
LOG_FILE="$SCRIPT_DIR/health_check.log"
FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/50bda5b5-3081-416d-8053-04d9ff6fd490"

echo "=== 健康检查开始 $(date -u) ===" > "$REPORT_FILE"

# Run health check
python3 health_check.py >> "$REPORT_FILE" 2>&1
EXIT_CODE=$?

echo "=== 健康检查完成 $(date -u) ===" >> "$REPORT_FILE"

# Append to main log
cat "$REPORT_FILE" >> "$LOG_FILE"

# Push to Feishu
if [ -n "$FEISHU_WEBHOOK" ]; then
    REPORT=$(cat "$REPORT_FILE" | head -200)
    if [ $EXIT_CODE -eq 0 ]; then
        TITLE="✅ 抖音来客系统健康检查完成"
        MSG_TYPE="success"
    else
        TITLE="❌ 抖音来客系统健康检查失败"
        MSG_TYPE="error"
    fi

    # Use notifier.py to send
    python3 <<EOF
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from notifier import Notifier

n = Notifier("$FEISHU_WEBHOOK")
n.send_feishu_message(
    "$TITLE",
    """
**报告**:
```
$(cat "$REPORT_FILE" | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g')
```
    """,
    "$MSG_TYPE"
)
EOF
fi

echo "报告生成: $REPORT_FILE"
echo "日志已追加: $LOG_FILE"
echo "飞书推送完成"
