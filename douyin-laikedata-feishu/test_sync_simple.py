#!/usr/bin/env python3
"""简化的同步测试脚本"""
import requests
import json
from datetime import datetime, timedelta
from urllib.parse import urlencode

# 读取 token
with open('.token_cache.json', 'r') as f:
    token_data = json.load(f)
    access_token = token_data['access_token']

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "REDACTED"
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

# 测试第一个账户
account_id = 1835880409219083
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

print(f"1. 获取数据: 账户 {account_id}, 日期 {yesterday}")

params = {
    'local_account_id': account_id,
    'start_date': yesterday,
    'end_date': yesterday,
    'time_granularity': 'TIME_GRANULARITY_DAILY',
    'metrics': json.dumps(['stat_cost', 'show_cnt', 'click_cnt', 'convert_cnt', 'clue_pay_order_cnt']),
    'page': 1,
    'page_size': 100
}

query_string = urlencode(params)
url = f'https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/?{query_string}'
headers = {'Access-Token': access_token}

resp = requests.get(url, headers=headers, timeout=10)
data = resp.json()

if data.get('code') == 0:
    promotion_list = data.get('data', {}).get('promotion_list', [])
    print(f"   ✓ 获取到 {len(promotion_list)} 条数据")
    
    if promotion_list:
        # 获取飞书 token
        print("\n2. 获取飞书 Token")
        auth_url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
        auth_resp = requests.post(auth_url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET})
        feishu_token = auth_resp.json()['tenant_access_token']
        print("   ✓ Token 获取成功")
        
        # 构建记录
        print("\n3. 构建飞书记录")
        records = []
        for item in promotion_list:
            cost = item.get('stat_cost', 0)
            convert = item.get('convert_cnt', 0)
            
            record = {
                "fields": {
                    "文本": "郑州天后医疗美容医院有限公司-XL",
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
            print(f"   - {item.get('promotion_name')}: 消耗 {cost} 元")
        
        # 写入飞书
        print(f"\n4. 写入 {len(records)} 条记录到飞书")
        write_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_create"
        write_headers = {
            "Authorization": f"Bearer {feishu_token}",
            "Content-Type": "application/json"
        }
        payload = {"records": records}
        
        write_resp = requests.post(write_url, headers=write_headers, json=payload, timeout=30)
        result = write_resp.json()
        
        if result.get('code') == 0:
            print("   ✅ 写入成功！")
        else:
            print(f"   ❌ 写入失败: {result}")
    else:
        print("   ⚠️  没有数据")
else:
    print(f"   ❌ 获取失败: {data}")
