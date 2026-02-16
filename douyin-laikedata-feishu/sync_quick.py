#!/usr/bin/env python3
"""
快速同步脚本 - 用于定时任务
只同步有数据的账户，避免超时
"""
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode
import sys

# 读取 token
with open('/root/.openclaw/workspace/douyin-laikedata-feishu/.token_cache.json', 'r') as f:
    token_data = json.load(f)
    ACCESS_TOKEN = token_data['access_token']

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "REDACTED"
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

# 只同步有数据的账户（从active_account_ids.py读取）
sys.path.insert(0, '/root/.openclaw/workspace/douyin-laikedata-feishu')
from active_account_ids import ACTIVE_ACCOUNT_IDS
from account_names import ACCOUNT_NAMES

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始同步")
print(f"活跃账户数: {len(ACTIVE_ACCOUNT_IDS)}")

yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
print(f"同步日期: {yesterday}")

all_data = []

for account_id in ACTIVE_ACCOUNT_IDS:
    params = {
        "local_account_id": account_id,
        "start_date": yesterday,
        "end_date": yesterday,
        "time_granularity": "TIME_GRANULARITY_DAILY",
        "metrics": json.dumps(["stat_cost", "show_cnt", "click_cnt", "convert_cnt", "clue_pay_order_cnt"]),
        "page": 1,
        "page_size": 100
    }
    
    query_string = urlencode(params)
    url = f"https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/?{query_string}"
    headers = {"Access-Token": ACCESS_TOKEN}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        
        if data.get('code') == 0:
            promotion_list = data.get('data', {}).get('promotion_list', [])
            if promotion_list:
                for item in promotion_list:
                    item['local_account_id'] = account_id
                all_data.extend(promotion_list)
                print(f"  ✓ {ACCOUNT_NAMES.get(account_id)}: {len(promotion_list)}条")
    except Exception as e:
        print(f"  ❌ {account_id}: {e}")

print(f"\n获取到 {len(all_data)} 条数据")

if all_data:
    # 获取飞书token
    auth_url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    auth_resp = requests.post(auth_url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET}, timeout=10)
    feishu_token = auth_resp.json()['tenant_access_token']
    
    # 构建记录
    records = []
    for item in all_data:
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
    
    # 写入飞书
    write_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_create"
    write_headers = {"Authorization": f"Bearer {feishu_token}", "Content-Type": "application/json"}
    payload = {"records": records}
    
    write_resp = requests.post(write_url, headers=write_headers, json=payload, timeout=30)
    result = write_resp.json()
    
    if result.get('code') == 0:
        print(f"✅ 写入成功: {len(records)}条")
    else:
        print(f"❌ 写入失败: {result}")
        sys.exit(1)
else:
    print("⚠️  没有数据")

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 完成")
