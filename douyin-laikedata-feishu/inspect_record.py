#!/usr/bin/env python3
"""
查看飞书记录的实际结构
"""
import requests
import json

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

token = get_feishu_token()

url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/search"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
payload = {
    "page_size": 1,
    "field_names": ["时间", "单元ID", "单元名称"]
}

resp = requests.post(url, headers=headers, json=payload, timeout=30)
result = resp.json()

if result.get('code') == 0:
    items = result.get('data', {}).get('items', [])
    if items:
        print("第一条记录的结构:")
        print(json.dumps(items[0], indent=2, ensure_ascii=False))
