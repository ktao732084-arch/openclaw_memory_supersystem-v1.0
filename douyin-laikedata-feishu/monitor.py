#!/usr/bin/env python3
"""
定时任务执行监控脚本
记录每次执行的结果到日志文件
"""
import json
from datetime import datetime
import os

LOG_FILE = "/root/.openclaw/workspace/douyin-laikedata-feishu/cron_execution.log"

def log_execution(status, message, details=None):
    """记录执行结果"""
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,  # success, error, warning
        "message": message,
        "details": details or {}
    }
    
    # 追加到日志文件
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    print(f"[{entry['timestamp']}] {status.upper()}: {message}")

def get_recent_logs(count=10):
    """获取最近的日志"""
    if not os.path.exists(LOG_FILE):
        return []
    
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    
    logs = []
    for line in lines[-count:]:
        try:
            logs.append(json.loads(line.strip()))
        except:
            pass
    
    return logs

def print_recent_logs(count=10):
    """打印最近的日志"""
    logs = get_recent_logs(count)
    
    if not logs:
        print("暂无执行记录")
        return
    
    print(f"\n最近 {len(logs)} 次执行记录：")
    print("=" * 80)
    
    for log in logs:
        status_icon = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️"
        }.get(log["status"], "ℹ️")
        
        print(f"{status_icon} [{log['timestamp']}] {log['message']}")
        if log.get("details"):
            for key, value in log["details"].items():
                print(f"   {key}: {value}")
    
    print("=" * 80)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "view":
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            print_recent_logs(count)
        elif sys.argv[1] == "log":
            status = sys.argv[2] if len(sys.argv) > 2 else "info"
            message = sys.argv[3] if len(sys.argv) > 3 else "Manual log entry"
            log_execution(status, message)
    else:
        print("用法:")
        print("  python3 monitor.py view [count]  - 查看最近的执行记录")
        print("  python3 monitor.py log <status> <message>  - 手动添加日志")
