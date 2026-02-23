#!/usr/bin/env python3
import requests

FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
TABLE_SHUNDING = "tblbIHSjDvlobJ4a"

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10)
    return resp.json()['tenant_access_token']

token = get_token()
print(f"Token: {token[:20]}...\n")

# 查顺鼎表字段
url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_SHUNDING}/fields"
resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
print("顺鼎表字段:")
if resp.json().get('code') == 0:
    for f in resp.json()['data']['items']:
        print(f"  - {f['field_name']} ({f['ui_type']})")

# 查顺鼎表前3条数据
print("\n顺鼎表前3条数据:")
url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_SHUNDING}/records?page_size=3"
resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
if resp.json().get('code') == 0:
    for i, r in enumerate(resp.json()['data']['items'], 1):
        print(f"\n记录 {i}:")
        print(r['fields'])
