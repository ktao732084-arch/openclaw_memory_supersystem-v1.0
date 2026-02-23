#!/usr/bin/env python3
"""
强制同步指定日期的数据（先删除再写入）
"""
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from token_manager import get_valid_token

LOCAL_ACCOUNT_ID = 1835880409219083

FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    resp = requests.post(url, json=payload, timeout=10)
    data = resp.json()
    return data.get('tenant_access_token') if data.get('code') == 0 else None

def get_juliang_data(date_str):
    print(f"📊 获取 {date_str} 的数据...")
    
    access_token = get_valid_token()
    if not access_token:
        return []
    
    params = {
        "local_account_id": LOCAL_ACCOUNT_ID,
        "start_date": date_str,
        "end_date": date_str,
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
            print(f"✓ 获取到 {len(promotion_list)} 条数据\n")
            return promotion_list
        else:
            print(f"❌ 获取失败: {data.get('message')}")
            return []
    except Exception as e:
        print(f"❌ 异常: {e}")
        return []

def delete_records_by_date(token, date_str):
    print(f"🗑️  删除 {date_str} 的旧数据...")
    
    # 查询该日期的记录
    search_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/search"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    payload = {
        "page_size": 500,
        "filter": {
            "conjunction": "and",
            "conditions": [{
                "field_name": "时间",
                "operator": "is",
                "value": [date_str]
            }]
        }
    }
    
    all_records = []
    page_token = None
    
    while True:
        if page_token:
            payload["page_token"] = page_token
        
        try:
            resp = requests.post(search_url, headers=headers, json=payload, timeout=30)
            result = resp.json()
            
            if result.get('code') == 0:
                data = result.get('data', {})
                items = data.get('items', [])
                all_records.extend(items)
                
                if not data.get('has_more'):
                    break
                page_token = data.get('page_token')
            else:
                break
        except Exception as e:
            print(f"   ⚠️  查询失败: {e}")
            break
    
    if not all_records:
        print("   没有需要删除的记录")
        return
    
    print(f"   找到 {len(all_records)} 条旧记录")
    
    # 批量删除
    delete_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_delete"
    record_ids = [r.get('record_id') for r in all_records if r.get('record_id')]
    
    batch_size = 500
    deleted = 0
    
    for i in range(0, len(record_ids), batch_size):
        batch = record_ids[i:i+batch_size]
        payload = {"records": batch}
        
        try:
            resp = requests.post(delete_url, headers=headers, json=payload, timeout=30)
            result = resp.json()
            
            if result.get('code') == 0:
                deleted += len(batch)
                print(f"   ✓ 删除 {len(batch)} 条")
            else:
                print(f"   ❌ 删除失败: {result.get('msg')}")
        except Exception as e:
            print(f"   ❌ 异常: {e}")
    
    print(f"   ✅ 共删除 {deleted} 条\n")

def write_to_feishu(token, data_list):
    print(f"📝 写入 {len(data_list)} 条数据...")
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_create"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    records = []
    for item in data_list:
        cost = item.get('stat_cost', 0)
        convert = item.get('convert_cnt', 0)
        convert_cost = round(cost / convert, 2) if convert > 0 else 0
        
        record = {
            "fields": {
                "时间": item.get('stat_time_day', ''),
                "单元ID": str(item.get('promotion_id', '')),
                "单元名称": item.get('promotion_name', ''),
                "消耗(元)": str(cost),
                "转化数": str(convert),
                "转化成本(元)": str(convert_cost),
                "团购线索数": str(item.get('clue_pay_order_cnt', 0))
            }
        }
        records.append(record)
    
    batch_size = 500
    success = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        payload = {"records": batch}
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            result = resp.json()
            
            if result.get('code') == 0:
                success += len(batch)
                print(f"   ✓ 写入 {len(batch)} 条")
            else:
                print(f"   ❌ 失败: {result.get('msg')}")
        except Exception as e:
            print(f"   ❌ 异常: {e}")
    
    print(f"   ✅ 共写入 {success} 条\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"💡 未指定日期，使用昨天: {date_str}\n")
    else:
        date_str = sys.argv[1]
    
    print("="*60)
    print(f"强制同步: {date_str}")
    print("="*60 + "\n")
    
    # 1. 获取数据
    data = get_juliang_data(date_str)
    
    if not data:
        print("⚠️  没有数据")
        exit(0)
    
    # 2. 获取飞书token
    token = get_feishu_token()
    if not token:
        print("❌ 无法获取飞书token")
        exit(1)
    
    # 3. 删除旧数据
    delete_records_by_date(token, date_str)
    
    # 4. 写入新数据
    write_to_feishu(token, data)
    
    print("="*60)
    print("✅ 同步完成")
    print("="*60)
