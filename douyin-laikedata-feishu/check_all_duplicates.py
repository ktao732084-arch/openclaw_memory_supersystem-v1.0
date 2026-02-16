#!/usr/bin/env python3
"""
批量检查和清理重复数据
"""
import subprocess
from datetime import datetime, timedelta

print("="*60)
print("批量检查重复数据")
print("="*60 + "\n")

# 检查最近10天
dates_to_check = []
for i in range(1, 13):  # 2月1日到12日
    date_str = f"2026-02-{i:02d}"
    dates_to_check.append(date_str)

duplicates_found = []

for date_str in dates_to_check:
    print(f"检查 {date_str}...", end=" ")
    
    result = subprocess.run(
        ["python3", "dedup.py", "check", date_str],
        capture_output=True,
        text=True,
        cwd="/root/.openclaw/workspace/douyin-laikedata-feishu"
    )
    
    if "发现重复数据" in result.stdout:
        print("❌ 有重复")
        duplicates_found.append(date_str)
    elif "没有重复数据" in result.stdout:
        print("✓ 正常")
    elif "没有数据" in result.stdout:
        print("- 无数据")
    else:
        print("? 未知")

if duplicates_found:
    print(f"\n⚠️  发现 {len(duplicates_found)} 个日期有重复数据:")
    for date in duplicates_found:
        print(f"   - {date}")
    
    print("\n💡 建议运行:")
    print("   python3 batch_force_sync.py")
else:
    print("\n✅ 所有日期都没有重复数据")

print("\n" + "="*60)
