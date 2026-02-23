#!/usr/bin/env python3
import requests

FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"

TABLE_SHUNDING = "tblbIHSjDvlobJ4a"
TABLE_KEZI = "tblYgY0c0PRVqoqe"
TABLE_PROMOTION = "tbl1n1PC1aooYdKk"

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10)
    return resp.json()['tenant_access_token']

token = get_token()

def get_fields(table_id):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/fields"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
    return [f['field_name'] for f in resp.json()['data']['items']]

print("顺鼎表字段:", get_fields(TABLE_SHUNDING))
print("客资表字段:", get_fields(TABLE_KEZI))
print("投放表字段:", get_fields(TABLE_PROMOTION))
