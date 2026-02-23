#!/usr/bin/env python3
"""
强制同步指定日期的多账户数据
"""
import requests
import json
from urllib.parse import urlencode
import sys

sys.path.insert(0, '/root/.openclaw/workspace/douyin-laikedata-feishu')
from token_manager import get_valid_token
from account_ids import ACCOUNT_IDS
from account_names import ACCOUNT_NAMES

FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def get_account_data(account_id, date):
    """获取单个账户的数据"""
    access_token = get_valid_token()
    if not access_token:
        return []
    
    params = {
        "local_account_id": account_id,
        "start_date": date,
        "end_date": date,
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
                # 添加账户ID
                for item in promotion_list:
                    item['local_account_id'] = account_id
            return promotion_list
        return []
    except:
        return []

def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET})
    return resp.json().get('tenant_access_token')

def delete_records_by_date(token, date):
    """删除指定日期的所有记录"""
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records'
    headers = {'Authorization': f'Bearer {token}'}
    
    # 获取所有记录
    all_records = []
    page_token = None
    while True:
        params = {'page_size': 500}
        if page_token:
            params['page_token'] = page_token
        
        resp = requests.get(url, headers=headers, params=params)
        data = resp.json()
        
        if data.get('code') != 0:
            break
        
        items = data.get('data', {}).get('items', [])
        all_records.extend(items)
        
        page_token = data.get('data', {}).get('page_token')
        if not page_token:
            break
    
    # 筛选指定日期的记录
    to_delete = [r['record_id'] for r in all_records if r.get('fields', {}).get('时间') == date]
    
    if not to_delete:
        print(f"   没有找到 {date} 的记录")
        return 0
    
    print(f"   找到 {len(to_delete)} 条旧记录")
    
    # 批量删除
    delete_url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_delete'
    batch_size = 500
    deleted = 0
    
    for i in range(0, len(to_delete), batch_size):
        batch = to_delete[i:i+batch_size]
        payload = {'records': batch}
        resp = requests.post(delete_url, headers=headers, json=payload)
        if resp.json().get('code') == 0:
            deleted += len(batch)
            print(f"   ✓ 删除 {len(batch)} 条")
    
    return deleted

def write_to_feishu(token, data_list):
    """写入数据到飞书"""
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
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_create"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    batch_size = 500
    written = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        payload = {"records": batch}
        resp = requests.post(url, headers=headers, json=payload)
        if resp.json().get('code') == 0:
            written += len(batch)
            print(f"   ✓ 写入 {len(batch)} 条")
    
    return written

def main():
    if len(sys.argv) < 2:
        print("用法: python3 force_sync_multi.py 2026-02-12")
        return
    
    date = sys.argv[1]
    
    print("=" * 60)
    print(f"强制同步多账户数据: {date}")
    print("=" * 60)
    
    # 1. 获取所有账户的数据
    print(f"\n📊 获取 {date} 的数据（77个账户）...")
    all_data = []
    success_accounts = 0
    
    for account_id in ACCOUNT_IDS:
        data = get_account_data(account_id, date)
        if data:
            all_data.extend(data)
            success_accounts += 1
            account_name = ACCOUNT_NAMES.get(account_id, f"账户{account_id}")
            print(f"   ✓ {account_name}: {len(data)} 条")
    
    print(f"\n   成功账户: {success_accounts}/{len(ACCOUNT_IDS)}")
    print(f"   总记录数: {len(all_data)} 条")
    
    if not all_data:
        print("\n⚠️  没有数据，退出")
        return
    
    # 2. 获取飞书token
    token = get_feishu_token()
    if not token:
        print("\n❌ 获取飞书token失败")
        return
    
    # 3. 删除旧数据
    print(f"\n🗑️  删除 {date} 的旧数据...")
    deleted = delete_records_by_date(token, date)
    print(f"   ✅ 共删除 {deleted} 条")
    
    # 4. 写入新数据
    print(f"\n📝 写入 {len(all_data)} 条数据...")
    written = write_to_feishu(token, all_data)
    print(f"   ✅ 共写入 {written} 条")
    
    print("\n" + "=" * 60)
    print("✅ 同步完成")
    print("=" * 60)

if __name__ == '__main__':
    main()
