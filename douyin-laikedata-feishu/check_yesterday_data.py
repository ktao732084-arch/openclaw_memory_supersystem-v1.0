#!/usr/bin/env python3
"""
详细检查昨天的数据情况
"""
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode

ACCESS_TOKEN = "REDACTED"
LOCAL_ACCOUNT_ID = 1835880409219083

yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

print("="*60)
print(f"详细检查 {yesterday} 的数据")
print("="*60 + "\n")

# 1. 检查有多少个项目在投放
print("1️⃣ 获取所有项目状态...\n")

url = "https://api.oceanengine.com/open_api/v3.0/local/project/list/"
headers = {
    "Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

params = {
    "local_account_id": LOCAL_ACCOUNT_ID,
    "page": 1,
    "page_size": 100
}

try:
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    data = resp.json()
    
    if data.get('code') == 0:
        projects = data.get('data', {}).get('project_list', [])
        total = data.get('data', {}).get('page_info', {}).get('total_number', 0)
        
        print(f"   总项目数: {total}")
        
        # 统计项目状态
        status_count = {}
        for proj in projects:
            status = proj.get('project_status_first', '未知')
            status_count[status] = status_count.get(status, 0) + 1
        
        print(f"\n   项目状态分布:")
        for status, count in status_count.items():
            status_name = "启用" if status == "PROJECT_STATUS_ENABLE" else "暂停"
            print(f"   - {status_name}: {count} 个")
        
except Exception as e:
    print(f"   ❌ 异常: {e}")

# 2. 检查报表数据（不带过滤条件）
print(f"\n2️⃣ 获取 {yesterday} 的报表数据...\n")

params = {
    "local_account_id": LOCAL_ACCOUNT_ID,
    "start_date": yesterday,
    "end_date": yesterday,
    "time_granularity": "TIME_GRANULARITY_DAILY",
    "metrics": json.dumps([
        "stat_cost",
        "show_cnt",
        "click_cnt",
        "convert_cnt",
        "clue_pay_order_cnt"
    ]),
    "page": 1,
    "page_size": 100
}

query_string = urlencode(params)
url = f"https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/?{query_string}"

headers = {"Access-Token": ACCESS_TOKEN}

try:
    resp = requests.get(url, headers=headers, timeout=10)
    data = resp.json()
    
    if data.get('code') == 0:
        page_info = data.get('data', {}).get('page_info', {})
        promotions = data.get('data', {}).get('promotion_list', [])
        
        print(f"   总数据量: {page_info.get('total_number', 0)}")
        print(f"   总页数: {page_info.get('total_page', 0)}")
        print(f"   当前页: {len(promotions)} 条\n")
        
        if promotions:
            print("   数据详情:")
            total_cost = 0
            for i, item in enumerate(promotions, 1):
                cost = item.get('stat_cost', 0)
                total_cost += cost
                print(f"   {i}. {item.get('promotion_name', '未知')}")
                print(f"      消耗: {cost}, 展示: {item.get('show_cnt', 0)}, 点击: {item.get('click_cnt', 0)}")
            
            print(f"\n   总消耗: {total_cost:.2f} 元")
        else:
            print("   ⚠️  没有数据！")
    else:
        print(f"   ❌ 错误: {data.get('message')}")
        
except Exception as e:
    print(f"   ❌ 异常: {e}")

# 3. 尝试获取账户维度数据
print(f"\n3️⃣ 尝试获取账户维度汇总数据...\n")

url = "https://api.oceanengine.com/open_api/v3.0/local/report/account/get/"

params = {
    "local_account_id": LOCAL_ACCOUNT_ID,
    "start_date": yesterday,
    "end_date": yesterday,
    "time_granularity": "TIME_GRANULARITY_DAILY",
    "metrics": json.dumps([
        "stat_cost",
        "show_cnt",
        "click_cnt",
        "convert_cnt",
        "clue_pay_order_cnt"
    ]),
    "page": 1,
    "page_size": 100
}

try:
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    data = resp.json()
    
    if data.get('code') == 0:
        account_data = data.get('data', {}).get('list', [])
        print(f"   账户数据: {json.dumps(account_data, indent=2, ensure_ascii=False)}")
    else:
        print(f"   ❌ 错误: {data.get('message')}")
        
except Exception as e:
    print(f"   ❌ 异常: {e}")

print("\n" + "="*60)
print("💡 分析:")
print("如果只有4条数据，可能是：")
print("1. 昨天确实只有4个单元在投放")
print("2. 其他单元没有消耗（消耗为0的不返回）")
print("3. 需要查看其他账户的数据")
print("="*60)
