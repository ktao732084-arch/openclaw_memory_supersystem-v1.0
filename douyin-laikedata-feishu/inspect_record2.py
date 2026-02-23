#!/usr/bin/env python3
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

# 使用 list 接口
url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
headers = {"Authorization": f"Bearer {token}"}
params = {"page_size": 1}

resp = requests.get(url, headers=headers, params=params, timeout=30)
result = resp.json()

print("响应:")
print(json.dumps(result, indent=2, ensure_ascii=False))
