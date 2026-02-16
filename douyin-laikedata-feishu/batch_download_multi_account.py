#!/usr/bin/env python3
"""
多账户批量下载历史数据
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
from account_names import ACCOUNT_NAMES

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "REDACTED"
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def get_account_data(account_id, start_date, end_date):
    """获取单个账户的数据"""
    access_token = get_valid_token()
    if not access_token:
        return []
    
    params = {
        "local_account_id": account_id,
        "start_date": start_date,
        "end_date": end_date,
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
            # 给每条数据添加账户ID
            for item in promotion_list:
                item['local_account_id'] = account_id
            return promotion_list
        else:
            return []
    except Exception as e:
        return []

def get_feishu_token():
    """获取飞书访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        
        if data.get('code') == 0:
            return data['tenant_access_token']
        else:
            return None
    except Exception as e:
        return None

def write_to_feishu(data_list):
    """写入数据到飞书"""
    if not data_list:
        return False
    
    token = get_feishu_token()
    if not token:
        return False
    
    # 构建记录
    records = []
    for item in data_list:
        cost = item.get('stat_cost', 0)
        convert = item.get('convert_cnt', 0)
        account_id = item.get('local_account_id')
        account_name = ACCOUNT_NAMES.get(account_id, f"账户{account_id}")
        
        record = {
            "fields": {
                "文本": account_name,
                "时间": item.get('stat_time_day', ''),
                "单元ID": str(item.get('promotion_id', '')),
                "单元名称": item.get('promotion_name', ''),
                "消耗(元)": str(cost),
                "转化数": str(convert),
                "转化成本(元)": str(round(cost / convert, 2)) if convert > 0 else "0",
                "团购线索数": str(item.get('clue_pay_order_cnt', 0))
            }
        }
        records.append(record)
    
    # 批量写入
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_create"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    batch_size = 500
    success_count = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        payload = {"records": batch}
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            result = resp.json()
            
            if result.get('code') == 0:
                success_count += len(batch)
                print(f"  ✓ 第 {i//batch_size + 1} 批写入成功: {len(batch)} 条")
            else:
                print(f"  ❌ 第 {i//batch_size + 1} 批失败: {result.get('msg')}")
        except Exception as e:
            print(f"  ❌ 写入失败: {e}")
    
    return success_count > 0

def main():
    """主流程"""
    if len(sys.argv) != 3:
        print("用法: python3 batch_download_multi_account.py <开始日期> <结束日期>")
        print("示例: python3 batch_download_multi_account.py 2026-02-01 2026-02-11")
        return
    
    start_date = sys.argv[1]
    end_date = sys.argv[2]
    
    print("="*60)
    print("多账户批量历史数据下载")
    print("="*60)
    print(f"日期范围: {start_date} 到 {end_date}")
    print(f"账户数量: {len(ACCOUNT_IDS)}")
    print()
    
    all_data = []
    success_accounts = 0
    
    for i, account_id in enumerate(ACCOUNT_IDS, 1):
        account_name = ACCOUNT_NAMES.get(account_id, f"账户{account_id}")
        print(f"[{i}/{len(ACCOUNT_IDS)}] {account_name}...", end=" ", flush=True)
        
        data = get_account_data(account_id, start_date, end_date)
        if data:
            all_data.extend(data)
            success_accounts += 1
            print(f"✓ {len(data)} 条")
        else:
            print("无数据")
    
    print()
    print(f"汇总:")
    print(f"  有数据账户: {success_accounts}/{len(ACCOUNT_IDS)}")
    print(f"  总记录数: {len(all_data)} 条")
    print()
    
    if all_data:
        print("写入飞书...")
        write_to_feishu(all_data)
        print()
        print("✅ 完成！")
    else:
        print("⚠️  没有数据")
    
    print("="*60)

if __name__ == '__main__':
    main()
