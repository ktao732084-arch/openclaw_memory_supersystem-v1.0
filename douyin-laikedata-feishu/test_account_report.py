#!/usr/bin/env python3
"""
尝试获取账户维度报表（可能包含多个账户）
"""
import requests
import json
from urllib.parse import urlencode
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from token_manager import get_valid_token

ADVERTISER_ID = 1769665409798152
LOCAL_ACCOUNT_ID = 1835880409219083

print("="*60)
print("尝试获取账户维度报表")
print("="*60 + "\n")

access_token = get_valid_token()
if not access_token:
    print("❌ 无法获取 Access Token")
    exit(1)

# 方法1: 使用 local_account_id 参数
print("🔍 方法1: 使用 local_account_id 参数\n")

params = {
    "local_account_id": LOCAL_ACCOUNT_ID,
    "start_date": "2026-02-12",
    "end_date": "2026-02-12",
    "time_granularity": "TIME_GRANULARITY_DAILY",
    "metrics": json.dumps(["stat_cost", "convert_cnt", "show_cnt"])
}

query_string = urlencode(params)
url = f"https://api.oceanengine.com/open_api/v3.0/local/report/account/get/?{query_string}"

headers = {"Access-Token": access_token}

try:
    resp = requests.get(url, headers=headers, timeout=10)
    data = resp.json()
    
    print(f"响应码: {data.get('code')}")
    print(f"消息: {data.get('message')}")
    
    if data.get('code') == 0:
        print("✅ 成功！\n")
        account_list = data.get('data', {}).get('account_list', [])
        print(f"找到 {len(account_list)} 个账户:\n")
        
        for acc in account_list:
            print(f"账户ID: {acc.get('local_account_id')}")
            print(f"  消耗: {acc.get('stat_cost', 0)} 元")
            print(f"  转化: {acc.get('convert_cnt', 0)} 个")
            print(f"  展示: {acc.get('show_cnt', 0)} 次")
            print()
    else:
        print(f"❌ 失败\n")
        
except Exception as e:
    print(f"❌ 异常: {e}\n")

# 方法2: 尝试不传 local_account_id，看是否返回所有账户
print("\n" + "="*60)
print("🔍 方法2: 不传 local_account_id（尝试获取所有账户）\n")

params = {
    "advertiser_id": ADVERTISER_ID,
    "start_date": "2026-02-12",
    "end_date": "2026-02-12",
    "time_granularity": "TIME_GRANULARITY_DAILY",
    "metrics": json.dumps(["stat_cost", "convert_cnt"])
}

query_string = urlencode(params)
url = f"https://api.oceanengine.com/open_api/v3.0/local/report/account/get/?{query_string}"

try:
    resp = requests.get(url, headers=headers, timeout=10)
    data = resp.json()
    
    print(f"响应码: {data.get('code')}")
    print(f"消息: {data.get('message')}")
    
    if data.get('code') == 0:
        print("✅ 成功！\n")
        account_list = data.get('data', {}).get('account_list', [])
        print(f"找到 {len(account_list)} 个账户:\n")
        
        for acc in account_list:
            print(f"账户ID: {acc.get('local_account_id')}")
            print(f"  消耗: {acc.get('stat_cost', 0)} 元")
            print(f"  转化: {acc.get('convert_cnt', 0)} 个")
            print()
    else:
        print(f"❌ 失败\n")
        
except Exception as e:
    print(f"❌ 异常: {e}\n")

# 方法3: 尝试获取账户列表接口
print("\n" + "="*60)
print("🔍 方法3: 获取本地推账户列表\n")

params = {
    "advertiser_id": ADVERTISER_ID,
    "page": 1,
    "page_size": 100
}

query_string = urlencode(params)
url = f"https://api.oceanengine.com/open_api/v3.0/local/account/list/?{query_string}"

try:
    resp = requests.get(url, headers=headers, timeout=10)
    data = resp.json()
    
    print(f"响应码: {data.get('code')}")
    print(f"消息: {data.get('message')}")
    
    if data.get('code') == 0:
        print("✅ 成功！\n")
        account_list = data.get('data', {}).get('account_list', [])
        print(f"找到 {len(account_list)} 个账户:\n")
        
        for acc in account_list:
            print(f"账户ID: {acc.get('local_account_id')}")
            print(f"  名称: {acc.get('local_account_name', 'N/A')}")
            print(f"  状态: {acc.get('status', 'N/A')}")
            print()
    else:
        print(f"❌ 失败\n")
        
except Exception as e:
    print(f"❌ 异常: {e}\n")

print("="*60)
print("💡 结论:")
print("如果以上方法都只返回1个账户，说明：")
print("1. 当前授权只能访问这1个本地推账户")
print("2. 或者确实只有1个本地推账户")
print("3. 需要在巨量后台确认账户数量")
print("="*60)
