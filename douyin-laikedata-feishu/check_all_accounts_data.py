#!/usr/bin/env python3
"""
检查所有账户昨天是否有数据
"""
import requests
import json
from datetime import datetime, timedelta
from token_manager import get_valid_token
from account_ids import ACCOUNT_IDS
from account_names import ACCOUNT_NAMES

def check_account_data(account_id, date_str, access_token):
    """检查单个账户是否有数据"""
    params = {
        "local_account_id": account_id,
        "start_date": date_str,
        "end_date": date_str,
        "time_granularity": "TIME_GRANULARITY_DAILY",
        "metrics": json.dumps(["stat_cost", "convert_cnt"]),
        "page": 1,
        "page_size": 10
    }
    
    url = f"https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/?{requests.compat.urlencode(params)}"
    headers = {"Access-Token": access_token}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        
        if data.get('code') == 0:
            promotion_list = data.get('data', {}).get('promotion_list', [])
            return len(promotion_list)
        else:
            return 0
    except:
        return 0

def main():
    print("="*60)
    print("检查所有账户数据（昨天）")
    print("="*60 + "\n")
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"日期: {yesterday}\n")
    
    access_token = get_valid_token()
    if not access_token:
        print("❌ 无法获取 Token")
        return
    
    print(f"开始检查 {len(ACCOUNT_IDS)} 个账户...\n")
    
    has_data = []
    no_data = []
    
    for i, account_id in enumerate(ACCOUNT_IDS, 1):
        account_name = ACCOUNT_NAMES.get(account_id, f"账户{account_id}")
        count = check_account_data(account_id, yesterday, access_token)
        
        if count > 0:
            has_data.append((account_id, account_name, count))
            print(f"  [{i:2d}/{len(ACCOUNT_IDS)}] ✅ {account_name}: {count} 条")
        else:
            no_data.append((account_id, account_name))
    
    print("\n" + "="*60)
    print(f"汇总:")
    print(f"  有数据: {len(has_data)} 个账户")
    print(f"  无数据: {len(no_data)} 个账户")
    print(f"  总记录: {sum(c for _, _, c in has_data)} 条")
    print("="*60)
    
    if has_data:
        print("\n有数据的账户:")
        for account_id, name, count in has_data:
            print(f"  {account_id}: {name} ({count} 条)")

if __name__ == '__main__':
    main()
