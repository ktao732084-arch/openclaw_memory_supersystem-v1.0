#!/usr/bin/env python3
"""
测试新的本地推账户ID
"""
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode

ACCESS_TOKEN = os.getenv('JULIANG_ACCESS_TOKEN')
NEW_ACCOUNT_ID = 272328498099752

def test_account_data(account_id):
    """测试账户数据"""
    print(f"🔍 测试账户ID: {account_id}\n")
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 测试单元维度数据
    print("1️⃣ 测试单元维度数据...")
    params = {
        "local_account_id": account_id,
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
        
        print(f"   状态码: {resp.status_code}")
        print(f"   响应: {json.dumps(data, indent=2, ensure_ascii=False)}\n")
        
        if data.get('code') == 0:
            promotion_list = data.get('data', {}).get('promotion_list', [])
            print(f"   ✅ 成功！获取到 {len(promotion_list)} 条数据\n")
            
            if promotion_list:
                print("   数据预览（前3条）:")
                for i, item in enumerate(promotion_list[:3], 1):
                    print(f"   {i}. {item.get('promotion_name', '未知')}")
                    print(f"      消耗: {item.get('stat_cost', 0)}, 转化: {item.get('convert_cnt', 0)}")
            
            return promotion_list
        else:
            print(f"   ❌ 失败: {data.get('message')}")
            return []
            
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        return []

def test_project_list(account_id):
    """测试项目列表"""
    print("\n2️⃣ 测试项目列表...")
    
    url = "https://api.oceanengine.com/open_api/v3.0/local/project/list/"
    
    headers = {
        "Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    params = {
        "local_account_id": account_id,
        "page": 1,
        "page_size": 10
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        data = resp.json()
        
        print(f"   状态码: {resp.status_code}")
        
        if data.get('code') == 0:
            projects = data.get('data', {}).get('project_list', [])
            total = data.get('data', {}).get('page_info', {}).get('total_number', 0)
            print(f"   ✅ 成功！共有 {total} 个项目\n")
            
            if projects:
                print("   项目预览（前3个）:")
                for i, proj in enumerate(projects[:3], 1):
                    print(f"   {i}. {proj.get('name', '未知')}")
                    print(f"      预算: {proj.get('project_budget', 0)}, 出价: {proj.get('project_bid', 0)}")
            
            return projects
        else:
            print(f"   ❌ 失败: {data.get('message')}")
            return []
            
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        return []

if __name__ == '__main__':
    print("="*60)
    print("测试新的本地推账户")
    print("="*60 + "\n")
    
    # 测试单元数据
    promotions = test_account_data(NEW_ACCOUNT_ID)
    
    # 测试项目列表
    projects = test_project_list(NEW_ACCOUNT_ID)
    
    print("\n" + "="*60)
    if promotions or projects:
        print("✅ 账户ID有效！")
    else:
        print("❌ 账户ID可能无效或没有数据")
    print("="*60)
