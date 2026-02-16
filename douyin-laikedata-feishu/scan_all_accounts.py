#!/usr/bin/env python3
"""
扫描所有账户，找出有数据的账户
"""
import requests
import json
from datetime import datetime
from urllib.parse import urlencode
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from token_manager import get_valid_token
from account_ids import ACCOUNT_IDS

print("="*60)
print("扫描所有账户（2026-02-11）")
print("="*60 + "\n")

test_date = "2026-02-11"

access_token = get_valid_token()
if not access_token:
    print("❌ 无法获取 Access Token")
    exit(1)

print(f"📋 总账户数: {len(ACCOUNT_IDS)}")
print(f"📅 测试日期: {test_date}\n")

accounts_with_data = []
accounts_no_data = []
accounts_error = []

for i, account_id in enumerate(ACCOUNT_IDS, 1):
    print(f"\r进度: {i}/{len(ACCOUNT_IDS)} ({i*100//len(ACCOUNT_IDS)}%)", end='', flush=True)
    
    params = {
        "local_account_id": account_id,
        "start_date": test_date,
        "end_date": test_date,
        "time_granularity": "TIME_GRANULARITY_DAILY",
        "metrics": json.dumps(["stat_cost"]),
        "page": 1,
        "page_size": 10  # API 要求至少为 10
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
                accounts_with_data.append(account_id)
            else:
                accounts_no_data.append(account_id)
        else:
            accounts_error.append((account_id, data.get('message', '未知错误')))
            
    except Exception as e:
        accounts_error.append((account_id, str(e)))

print("\n\n" + "="*60)
print("扫描结果")
print("="*60 + "\n")

print(f"✅ 有数据的账户: {len(accounts_with_data)} 个")
if accounts_with_data:
    for acc_id in accounts_with_data:
        print(f"   - {acc_id}")

print(f"\n⚠️  无数据的账户: {len(accounts_no_data)} 个")

print(f"\n❌ 错误的账户: {len(accounts_error)} 个")
if accounts_error:
    for acc_id, error in accounts_error[:10]:
        print(f"   - {acc_id}: {error}")
    if len(accounts_error) > 10:
        print(f"   ... 还有 {len(accounts_error) - 10} 个")

# 保存有数据的账户
if accounts_with_data:
    output_file = '/root/.openclaw/workspace/douyin-laikedata-feishu/active_account_ids.py'
    with open(output_file, 'w') as f:
        f.write("# 有数据的账户ID列表\n")
        f.write(f"# 扫描日期: {test_date}\n")
        f.write("ACTIVE_ACCOUNT_IDS = [\n")
        for acc_id in accounts_with_data:
            f.write(f"    {acc_id},\n")
        f.write("]\n")
    
    print(f"\n💾 有数据的账户已保存到: {output_file}")

print("\n" + "="*60)
