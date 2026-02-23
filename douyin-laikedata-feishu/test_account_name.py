#!/usr/bin/env python3
"""
测试账户名称写入
"""
import requests
import json
from datetime import datetime
from urllib.parse import urlencode
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from token_manager import get_valid_token
from account_names import ACCOUNT_NAMES

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

print("="*60)
print("测试账户名称写入")
print("="*60 + "\n")

# 测试账户
test_account = 1835880409219083
test_date = "2026-02-12"

print(f"测试账户: {test_account}")
print(f"账户名称: {ACCOUNT_NAMES.get(test_account, '未找到')}")
print(f"测试日期: {test_date}\n")

# 获取数据
access_token = get_valid_token()
params = {
    "local_account_id": test_account,
    "start_date": test_date,
    "end_date": test_date,
    "time_granularity": "TIME_GRANULARITY_DAILY",
    "metrics": json.dumps(["stat_cost", "convert_cnt"]),
    "page": 1,
    "page_size": 10
}

query_string = urlencode(params)
url = f"https://api.oceanengine.com/open_api/v3.0/local/report/promotion/get/?{query_string}"

resp = requests.get(url, headers={"Access-Token": access_token}, timeout=10)
data = resp.json()

if data.get('code') == 0:
    items = data.get('data', {}).get('promotion_list', [])
    print(f"✓ 获取到 {len(items)} 条数据\n")
    
    if items:
        # 添加账户ID
        for item in items:
            item['local_account_id'] = test_account
        
        # 构建记录
        test_item = items[0]
        account_name = ACCOUNT_NAMES.get(test_account, f'账户{test_account}')
        
        record = {
            "fields": {
                "文本": account_name,
                "时间": test_item.get('stat_time_day', ''),
                "单元ID": str(test_item.get('promotion_id', '')),
                "单元名称": test_item.get('promotion_name', ''),
                "消耗(元)": str(test_item.get('stat_cost', 0)),
                "转化数": str(test_item.get('convert_cnt', 0)),
                "转化成本(元)": "0",
                "团购线索数": "0"
            }
        }
        
        print("准备写入的记录:")
        print(json.dumps(record, indent=2, ensure_ascii=False))
        print()
        
        # 获取飞书token
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        resp = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10)
        feishu_token = resp.json()['tenant_access_token']
        
        # 写入飞书
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_create"
        headers = {
            "Authorization": f"Bearer {feishu_token}",
            "Content-Type": "application/json"
        }
        payload = {"records": [record]}
        
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        result = resp.json()
        
        print("飞书响应:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result.get('code') == 0:
            print("\n✅ 写入成功！")
        else:
            print(f"\n❌ 写入失败: {result.get('msg')}")
else:
    print(f"❌ 获取数据失败: {data.get('message')}")
