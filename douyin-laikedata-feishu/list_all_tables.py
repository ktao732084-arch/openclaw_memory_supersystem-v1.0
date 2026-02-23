#!/usr/bin/env python3
import requests

FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10)
    return resp.json()['tenant_access_token']

token = get_token()

# 获取所有表
url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables"
resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
result = resp.json()

if result.get('code') == 0:
    print("飞书多维表格中的所有表：\n")
    for table in result['data']['items']:
        print(f"  表名: {table['name']}")
        print(f"  表ID: {table['table_id']}")
        print()
else:
    print(f"错误: {result}")
