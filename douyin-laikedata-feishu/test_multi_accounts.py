#!/usr/bin/env python3
"""
测试多账户数据获取（前3个账户）
"""
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from token_manager import get_valid_token
from account_ids import ACCOUNT_IDS

print("="*60)
print("测试多账户数据获取")
print("="*60)
print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

print(f"📋 总账户数: {len(ACCOUNT_IDS)}")
print(f"📋 测试前3个账户\n")

# 测试日期：2026-02-11（已知有数据）
test_date = "2026-02-11"

access_token = get_valid_token()
if not access_token:
    print("❌ 无法获取 Access Token")
    exit(1)

# 测试前3个账户
test_accounts = ACCOUNT_IDS[:3]
all_data = []
success_count = 0

for i, account_id in enumerate(test_accounts, 1):
    print(f"\n{i}. 测试账户 {account_id}")
    print("-"*60)
    
    params = {
        "local_account_id": account_id,
        "start_date": test_date,
        "end_date": test_date,
        "time_granularity": "TIME_GRANULARITY_DAILY",
        "metrics": json.dumps(["stat_cost", "show_cnt", "click_cnt", "convert_cnt", "clue_pay_order_cnt"]),
        "page": 1,
        "page_size": 100
    }
    
    query_string = urlencode(params)
    url = f"https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/?{query_string}"
    
    headers = {"Access-Token": access_token}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        
        if data.get('code') == 0:
            promotion_list = data.get('data', {}).get('promotion_list', [])
            
            if promotion_list:
                print(f"   ✅ 成功！获取到 {len(promotion_list)} 条数据")
                all_data.extend(promotion_list)
                success_count += 1
                
                # 显示第一条数据
                first = promotion_list[0]
                print(f"   示例: {first.get('promotion_name', 'N/A')}")
                print(f"   消耗: {first.get('stat_cost', 0)} 元")
            else:
                print(f"   ⚠️  成功但无数据（该账户在 {test_date} 可能没有投放）")
        else:
            error_msg = data.get('message', '未知错误')
            print(f"   ❌ 失败: {error_msg}")
            
    except Exception as e:
        print(f"   ❌ 异常: {e}")

print("\n" + "="*60)
print("测试结果汇总")
print("="*60)
print(f"成功账户: {success_count}/3")
print(f"总记录数: {len(all_data)} 条")

if all_data:
    total_cost = sum(item.get('stat_cost', 0) for item in all_data)
    total_convert = sum(item.get('convert_cnt', 0) for item in all_data)
    
    print(f"总消耗: {total_cost:.2f} 元")
    print(f"总转化: {total_convert} 个")
    
    if total_convert > 0:
        avg_cost = total_cost / total_convert
        print(f"平均转化成本: {avg_cost:.2f} 元")

print("\n💡 如果测试成功，可以运行完整同步:")
print("   python3 multi_account_sync.py")
print("="*60)
