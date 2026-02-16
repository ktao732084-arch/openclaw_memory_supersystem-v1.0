#!/usr/bin/env python3
"""
最终测试：获取所有可访问的本地推账户
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
print("获取所有本地推账户")
print("="*60 + "\n")

access_token = get_valid_token()
if not access_token:
    print("❌ 无法获取 Access Token")
    exit(1)

# 方法1: 账户维度报表（使用有数据的日期）
print("🔍 方法1: 账户维度报表（2026-02-11）\n")

params = {
    "local_account_id": LOCAL_ACCOUNT_ID,
    "start_date": "2026-02-11",
    "end_date": "2026-02-11",
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

# 方法2: 获取账户列表（修复JSON解析）
print("\n" + "="*60)
print("🔍 方法2: 获取本地推账户列表\n")

params = {
    "advertiser_id": ADVERTISER_ID,
    "page": 1,
    "page_size": 100
}

query_string = urlencode(params)
url = f"https://api.oceanengine.com/open_api/v3.0/local/account/list/?{query_string}"

try:
    resp = requests.get(url, headers=headers, timeout=10)
    
    # 先打印原始响应
    print(f"HTTP 状态码: {resp.status_code}")
    print(f"响应内容: {resp.text[:200]}...\n")
    
    # 尝试解析JSON
    try:
        data = resp.json()
        print(f"响应码: {data.get('code')}")
        print(f"消息: {data.get('message')}")
        
        if data.get('code') == 0:
            print("✅ 成功！\n")
            account_list = data.get('data', {}).get('account_list', [])
            page_info = data.get('data', {}).get('page_info', {})
            
            print(f"找到 {len(account_list)} 个账户")
            print(f"总数: {page_info.get('total_count', 'N/A')}\n")
            
            for acc in account_list:
                print(f"账户ID: {acc.get('local_account_id')}")
                print(f"  名称: {acc.get('local_account_name', 'N/A')}")
                print(f"  状态: {acc.get('status', 'N/A')}")
                print()
        else:
            print(f"❌ 失败\n")
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        print(f"   可能是 HTML 错误页面或非标准响应")
        
except Exception as e:
    print(f"❌ 异常: {e}\n")

# 方法3: 尝试项目列表（看是否有多个账户的项目）
print("\n" + "="*60)
print("🔍 方法3: 通过项目列表查找账户\n")

params = {
    "local_account_id": LOCAL_ACCOUNT_ID,
    "page": 1,
    "page_size": 100
}

query_string = urlencode(params)
url = f"https://api.oceanengine.com/open_api/v3.0/local/project/list/?{query_string}"

try:
    resp = requests.get(url, headers=headers, timeout=10)
    data = resp.json()
    
    print(f"响应码: {data.get('code')}")
    print(f"消息: {data.get('message')}")
    
    if data.get('code') == 0:
        print("✅ 成功！\n")
        project_list = data.get('data', {}).get('project_list', [])
        page_info = data.get('data', {}).get('page_info', {})
        
        print(f"找到 {len(project_list)} 个项目")
        print(f"总数: {page_info.get('total_count', 'N/A')}\n")
        
        # 统计账户ID
        account_ids = {}
        for proj in project_list:
            acc_id = proj.get('local_account_id')
            if acc_id:
                if acc_id not in account_ids:
                    account_ids[acc_id] = []
                account_ids[acc_id].append(proj.get('project_name', 'N/A'))
        
        print(f"涉及 {len(account_ids)} 个账户:\n")
        for acc_id, projects in account_ids.items():
            print(f"账户ID: {acc_id}")
            print(f"  项目数: {len(projects)}")
            print(f"  示例项目: {projects[0] if projects else 'N/A'}")
            print()
    else:
        print(f"❌ 失败\n")
        
except Exception as e:
    print(f"❌ 异常: {e}\n")

print("="*60)
print("📊 总结:")
print("="*60)
print("\n根据测试结果：")
print("1. 如果方法1返回1个账户 → 当前只能访问1个账户")
print("2. 如果方法2返回多个账户 → 可以获取账户列表")
print("3. 如果方法3显示多个账户ID → 说明有多个账户")
print("\n如果确认有多个账户但API无法获取，可能需要：")
print("- 在巨量后台手动查看账户列表")
print("- 提供账户ID列表，我们可以批量获取数据")
print("="*60)
