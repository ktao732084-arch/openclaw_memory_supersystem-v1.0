#!/usr/bin/env python3
"""
测试本地推报表 API（POST方法）
"""
import requests
import json
from datetime import datetime, timedelta

ACCESS_TOKEN = "REDACTED"
LOCAL_ACCOUNT_ID = 1835880409219083

def test_local_report_post():
    """使用 POST 方法测试"""
    print("📊 测试本地推报表（POST方法）...\n")
    
    url = "https://api.oceanengine.com/open_api/v3.0/local/report/account/get/"
    
    headers = {
        "Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    payload = {
        "local_account_id": LOCAL_ACCOUNT_ID,
        "start_date": yesterday,
        "end_date": yesterday,
        "time_granularity": "TIME_GRANULARITY_DAILY",
        "metrics": [
            "stat_cost",
            "show_cnt",
            "click_cnt"
        ]
    }
    
    print(f"请求体:\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n")
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        
        print(f"状态码: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"响应:\n{json.dumps(data, indent=2, ensure_ascii=False)}\n")
            
            if data.get('code') == 0:
                print("✅ 成功！")
                return data
            else:
                print(f"❌ 错误: {data.get('message')}")
        else:
            print(f"原始响应: {resp.text[:500]}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    return None

if __name__ == '__main__':
    test_local_report_post()
