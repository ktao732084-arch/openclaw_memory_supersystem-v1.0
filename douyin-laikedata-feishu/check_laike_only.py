#!/usr/bin/env python3
import requests

FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
TABLE_LAIKE = "tbl3Oyi6JYt3ZUIP"

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10)
    return resp.json()['tenant_access_token']

token = get_token()

print("来客抓取实际数据 - 字段:")
url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_LAIKE}/fields"
resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
if resp.json().get('code') == 0:
    for f in resp.json()['data']['items']:
        print(f"  - {f['field_name']}")

print("\n来客抓取实际数据 - 前3条:")
url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_LAIKE}/records?page_size=3"
resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
if resp.json().get('code') == 0:
    for i, r in enumerate(resp.json()['data']['items'], 1):
        print(f"\n记录 {i}:")
        print(r['fields'])
