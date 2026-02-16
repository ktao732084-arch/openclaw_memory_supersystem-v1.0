#!/usr/bin/env python3
"""
尝试获取所有本地推账户的数据
"""
import requests
import json
from datetime import datetime, timedelta

ACCESS_TOKEN = "REDACTED"
ADVERTISER_ID = 1769665409798152

def get_account_level_data():
    """尝试获取账户维度的数据（可能包含多个账户）"""
    print("🔍 尝试获取账户维度数据...\n")
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    url = "https://api.oceanengine.com/open_api/v3.0/local/report/account/get/"
    
    headers = {
        "Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    # 尝试不指定 local_account_id，看能否获取所有账户
    params = {
        "advertiser_id": ADVERTISER_ID,
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
    
    print(f"请求参数: {json.dumps(params, indent=2, ensure_ascii=False)}\n")
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"状态码: {resp.status_code}")
        
        data = resp.json()
        print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}\n")
        
        if data.get('code') == 0:
            accounts = data.get('data', {}).get('list', [])
            print(f"✅ 找到 {len(accounts)} 个账户的数据")
            
            for acc in accounts:
                print(f"\n账户ID: {acc.get('local_account_id')}")
                print(f"账户名称: {acc.get('local_account_name', '未知')}")
                print(f"消耗: {acc.get('stat_cost', 0)}")
            
            return accounts
        else:
            print(f"❌ 错误: {data.get('message')}")
            return None
            
    except Exception as e:
        print(f"❌ 异常: {e}")
        return None

def get_promotion_data_without_account():
    """尝试不指定账户ID，获取所有单元数据"""
    print("\n" + "="*60)
    print("🔍 尝试获取所有单元数据（不指定账户）...\n")
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    url = "https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/"
    
    headers = {
        "Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    params = {
        "advertiser_id": ADVERTISER_ID,
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
    
    print(f"请求参数: {json.dumps(params, indent=2, ensure_ascii=False)}\n")
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"状态码: {resp.status_code}")
        
        data = resp.json()
        print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}\n")
        
        if data.get('code') == 0:
            promotions = data.get('data', {}).get('list', [])
            print(f"✅ 找到 {len(promotions)} 条单元数据")
            
            # 统计不同账户
            account_ids = set()
            for promo in promotions:
                if 'local_account_id' in promo:
                    account_ids.add(promo['local_account_id'])
            
            print(f"\n涉及 {len(account_ids)} 个账户:")
            for acc_id in account_ids:
                print(f"  - {acc_id}")
            
            return promotions
        else:
            print(f"❌ 错误: {data.get('message')}")
            return None
            
    except Exception as e:
        print(f"❌ 异常: {e}")
        return None

if __name__ == '__main__':
    # 方法1: 账户维度
    accounts = get_account_level_data()
    
    # 方法2: 单元维度（不指定账户）
    promotions = get_promotion_data_without_account()
    
    print("\n" + "="*60)
    print("总结:")
    if accounts:
        print(f"✅ 账户维度: 找到 {len(accounts)} 个账户")
    if promotions:
        print(f"✅ 单元维度: 找到 {len(promotions)} 条数据")
    print("="*60)
