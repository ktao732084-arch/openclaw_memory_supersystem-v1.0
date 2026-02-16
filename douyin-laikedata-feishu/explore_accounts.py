#!/usr/bin/env python3
"""
探索巨量引擎账户结构
尝试找到所有可访问的本地推账户
"""
import requests
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from token_manager import get_valid_token

# 已知信息
ADVERTISER_ID = 1769665409798152  # 广告主ID
KNOWN_ACCOUNT_ID = 1835880409219083  # 已知的本地推账户ID

def test_api_endpoint(endpoint, params, description):
    """测试 API 端点"""
    print(f"\n{'='*60}")
    print(f"测试: {description}")
    print(f"端点: {endpoint}")
    print(f"{'='*60}")
    
    access_token = get_valid_token()
    if not access_token:
        print("❌ 无法获取 Access Token")
        return None
    
    headers = {
        "Access-Token": access_token,
        "Content-Type": "application/json"
    }
    
    try:
        resp = requests.get(endpoint, headers=headers, params=params, timeout=10)
        data = resp.json()
        
        print(f"\n📊 响应:")
        print(f"   状态码: {data.get('code')}")
        print(f"   消息: {data.get('message')}")
        
        if data.get('code') == 0:
            print(f"   ✅ 成功！")
            return data.get('data')
        else:
            print(f"   ❌ 失败")
            return None
            
    except Exception as e:
        print(f"❌ 异常: {e}")
        return None

def main():
    print("="*60)
    print("巨量引擎账户结构探索")
    print("="*60)
    
    # 1. 尝试获取广告主下的所有本地推账户
    print("\n\n🔍 方法1: 获取广告主下的本地推账户列表")
    data = test_api_endpoint(
        "https://api.oceanengine.com/open_api/v3.0/local/account/list/",
        {"advertiser_id": ADVERTISER_ID},
        "本地推账户列表"
    )
    
    if data:
        accounts = data.get('account_list', [])
        print(f"\n   找到 {len(accounts)} 个账户:")
        for acc in accounts:
            print(f"   - ID: {acc.get('local_account_id')}")
            print(f"     名称: {acc.get('local_account_name', 'N/A')}")
            print(f"     状态: {acc.get('status', 'N/A')}")
    
    # 2. 尝试获取项目列表（可能包含多个账户的项目）
    print("\n\n🔍 方法2: 通过项目列表反推账户")
    data = test_api_endpoint(
        "https://api.oceanengine.com/open_api/v3.0/local/project/list/",
        {
            "local_account_id": KNOWN_ACCOUNT_ID,
            "page": 1,
            "page_size": 100
        },
        "项目列表"
    )
    
    if data:
        projects = data.get('project_list', [])
        print(f"\n   找到 {len(projects)} 个项目")
        
        # 统计账户ID
        account_ids = set()
        for proj in projects:
            acc_id = proj.get('local_account_id')
            if acc_id:
                account_ids.add(acc_id)
        
        print(f"   涉及 {len(account_ids)} 个账户:")
        for acc_id in sorted(account_ids):
            count = sum(1 for p in projects if p.get('local_account_id') == acc_id)
            print(f"   - {acc_id}: {count} 个项目")
    
    # 3. 尝试获取广告主信息
    print("\n\n🔍 方法3: 获取广告主信息")
    data = test_api_endpoint(
        "https://api.oceanengine.com/open_api/2/advertiser/info/",
        {"advertiser_ids": json.dumps([ADVERTISER_ID])},
        "广告主信息"
    )
    
    if data:
        advertisers = data.get('list', [])
        if advertisers:
            adv = advertisers[0]
            print(f"\n   广告主信息:")
            print(f"   - ID: {adv.get('id')}")
            print(f"   - 名称: {adv.get('name', 'N/A')}")
            print(f"   - 公司: {adv.get('company', 'N/A')}")
    
    # 4. 尝试获取账户维度报表（可能显示所有账户）
    print("\n\n🔍 方法4: 账户维度报表")
    data = test_api_endpoint(
        "https://api.oceanengine.com/open_api/v3.0/local/report/account/get/",
        {
            "advertiser_id": ADVERTISER_ID,
            "start_date": "2026-02-12",
            "end_date": "2026-02-12",
            "time_granularity": "TIME_GRANULARITY_DAILY",
            "metrics": json.dumps(["stat_cost", "convert_cnt"])
        },
        "账户维度报表"
    )
    
    if data:
        accounts = data.get('account_list', [])
        print(f"\n   找到 {len(accounts)} 个有数据的账户:")
        for acc in accounts:
            print(f"   - 账户ID: {acc.get('local_account_id')}")
            print(f"     消耗: {acc.get('stat_cost', 0)} 元")
            print(f"     转化: {acc.get('convert_cnt', 0)} 个")
    
    # 5. 尝试直接查询多个账户的数据（如果知道ID）
    print("\n\n🔍 方法5: 测试其他可能的账户ID")
    print("   (基于已知ID推测相邻ID)")
    
    # 尝试相邻的几个ID
    test_ids = [
        KNOWN_ACCOUNT_ID - 1,
        KNOWN_ACCOUNT_ID + 1,
        KNOWN_ACCOUNT_ID - 100,
        KNOWN_ACCOUNT_ID + 100,
    ]
    
    for test_id in test_ids:
        print(f"\n   测试 ID: {test_id}")
        data = test_api_endpoint(
            "https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/",
            {
                "local_account_id": test_id,
                "start_date": "2026-02-12",
                "end_date": "2026-02-12",
                "time_granularity": "TIME_GRANULARITY_DAILY",
                "metrics": json.dumps(["stat_cost"]),
                "page": 1,
                "page_size": 1
            },
            f"测试账户 {test_id}"
        )
        
        if data:
            promotions = data.get('promotion_list', [])
            if promotions:
                print(f"   ✅ 账户 {test_id} 存在且有数据！")
            else:
                print(f"   ⚠️  账户 {test_id} 存在但无数据")
    
    print("\n\n" + "="*60)
    print("探索完成")
    print("="*60)
    print("\n💡 建议:")
    print("1. 如果方法1成功，说明可以获取所有账户列表")
    print("2. 如果方法4成功，说明可以通过报表接口获取所有账户")
    print("3. 如果都失败，可能需要在巨量后台手动查看账户列表")
    print("4. 或者联系巨量引擎技术支持确认账户结构")

if __name__ == '__main__':
    main()
