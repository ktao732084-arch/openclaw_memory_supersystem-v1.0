#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

REPORT_FILE="$SCRIPT_DIR/sync_report.txt"
LOG_FILE="$SCRIPT_DIR/cron_execution.log"
FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/50bda5b5-3081-416d-8053-04d9ff6fd490"

echo "=== 数据同步开始 $(date -u) ===" > "$REPORT_FILE"

# Run sync
python3 sync_stable.py >> "$REPORT_FILE" 2>&1
EXIT_CODE=$?

# 更新上门标记
echo "=== 更新上门标记 $(date -u) ===" >> "$REPORT_FILE"
python3 update_arrival_mark.py >> "$REPORT_FILE" 2>&1

echo "=== 数据同步完成 $(date -u) ===" >> "$REPORT_FILE"

# Append to main log
cat "$REPORT_FILE" >> "$LOG_FILE"

# Push to Feishu with structured data
if [ -n "$FEISHU_WEBHOOK" ]; then
    python3 << 'PYEOF'
import os
import sys
import re

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)
from notifier import Notifier

report_file = os.path.join(script_dir, "sync_report.txt")
webhook = "https://open.feishu.cn/open-apis/bot/v2/hook/50bda5b5-3081-416d-8053-04d9ff6fd490"

with open(report_file, "r") as f:
    report = f.read()

exit_code = int(os.environ.get("SYNC_EXIT_CODE", "0"))

# 提取关键数据
sync_date = re.search(r"同步日期 = (\S+)", report)
sync_date = sync_date.group(1) if sync_date else "未知"

total_records = re.search(r"总记录数: (\d+)", report)
total_records = total_records.group(1) if total_records else "0"

accounts_ok = re.search(r"成功获取 (\d+)/(\d+) 个账户", report)
accounts_str = f"{accounts_ok.group(1)}/{accounts_ok.group(2)}" if accounts_ok else "未知"

# 提取各账户数据
account_lines = re.findall(r"获取: (.+?)\n.+?(?:✅ (\d+) 条|⚠️  无数据)", report)
account_details = []
for name, count in account_lines:
    if count:
        account_details.append(f"✅ {name}: {count} 条")
    else:
        account_details.append(f"➖ {name}: 无数据")

n = Notifier(webhook)

if exit_code == 0:
    content = [
        f"**同步日期**: {sync_date}",
        f"**有效账户**: {accounts_str}",
        f"**总记录数**: {total_records} 条",
        "",
        "**各账户明细**:",
    ] + account_details
    n.send_feishu_message("抖音来客数据同步完成", content, "success")
else:
    # 失败时附上错误日志
    error_lines = [l for l in report.split("\n") if "ERROR" in l or "❌" in l or "失败" in l]
    content = [
        f"**同步日期**: {sync_date}",
        f"**错误信息**: {'; '.join(error_lines[:3]) if error_lines else '见日志'}",
    ]
    n.send_feishu_message("抖音来客数据同步失败", content, "error")

PYEOF
fi

echo "报告生成: $REPORT_FILE"
echo "日志已追加: $LOG_FILE"
echo "飞书推送完成"
