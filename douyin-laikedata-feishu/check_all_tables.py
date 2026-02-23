#!/usr/bin/env python3
import requests

FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"

TABLE_SHUNDING = "tblbIHSjDvlobJ4a"  # 顺鼎
TABLE_KEZI = "tblYgY0c0PRVqoqe"     # 客资
TABLE_PROMOTION = "tbl1n1PC1aooYdKk" # 投放

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10)
    return resp.json()['tenant_access_token']

token = get_token()

def check_table(table_id, name):
    print(f"\n{'='*60}")
    print(f"📊 {name}")
    print(f"{'='*60}")
    
    # 字段
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/fields"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
    if resp.json().get('code') == 0:
        print("\n字段:")
        for f in resp.json()['data']['items']:
            print(f"  - {f['field_name']}")
    
    # 前3条数据
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records?page_size=3"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
    if resp.json().get('code') == 0:
        print("\n前3条数据:")
        for i, r in enumerate(resp.json()['data']['items'], 1):
            print(f"\n记录 {i}:")
            print(r['fields'])

check_table(TABLE_SHUNDING, "顺鼎数据")
check_table(TABLE_KEZI, "客资数据")
check_table(TABLE_PROMOTION, "投放数据")
