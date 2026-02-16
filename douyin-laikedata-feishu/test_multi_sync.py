#!/usr/bin/env python3
"""
测试多账户同步（使用有数据的7个账户）
"""
import requests
import json
from datetime import datetime
from urllib.parse import urlencode
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from token_manager import get_valid_token
from active_account_ids import ACTIVE_ACCOUNT_IDS

print("="*60)
print("测试多账户数据同步")
print("="*60)
print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

print(f"📋 有数据的账户: {len(ACTIVE_ACCOUNT_IDS)} 个")
for acc_id in ACTIVE_ACCOUNT_IDS:
    print(f"  - {acc_id}")
print()

# 测试日期：2026-02-11
test_date = "2026-02-11"
print(f"📅 测试日期: {test_date}\n")

access_token = get_valid_token()
if not access_token:
    print("❌ 无法获取 Access Token")
    exit(1)

# 获取所有账户的数据
all_data = []
success_count = 0

for i, account_id in enumerate(ACTIVE_ACCOUNT_IDS, 1):
    print(f"{i}. 账户 {account_id}")
    
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
                print(f"   ✅ 获取到 {len(promotion_list)} 条数据")
                all_data.extend(promotion_list)
                success_count += 1
                
                # 显示第一条
                first = promotion_list[0]
                print(f"   示例: {first.get('promotion_name', 'N/A')[:30]}")
                print(f"   消耗: {first.get('stat_cost', 0)} 元")
            else:
                print(f"   ⚠️  无数据")
        else:
            print(f"   ❌ 失败: {data.get('message')}")
            
    except Exception as e:
        print(f"   ❌ 异常: {e}")
    
    print()

print("="*60)
print("汇总结果")
print("="*60)
print(f"成功账户: {success_count}/{len(ACTIVE_ACCOUNT_IDS)}")
print(f"总记录数: {len(all_data)} 条\n")

if all_data:
    total_cost = sum(item.get('stat_cost', 0) for item in all_data)
    total_convert = sum(item.get('convert_cnt', 0) for item in all_data)
    total_clue = sum(item.get('clue_pay_order_cnt', 0) for item in all_data)
    
    print(f"总消耗: {total_cost:.2f} 元")
    print(f"总转化: {total_convert} 个")
    print(f"团购线索: {total_clue} 个")
    
    if total_convert > 0:
        avg_cost = total_cost / total_convert
        print(f"平均转化成本: {avg_cost:.2f} 元")
    
    print(f"\n✅ 测试成功！可以运行完整同步:")
    print(f"   python3 multi_account_sync.py")
else:
    print("⚠️  没有获取到数据")

print("="*60)
