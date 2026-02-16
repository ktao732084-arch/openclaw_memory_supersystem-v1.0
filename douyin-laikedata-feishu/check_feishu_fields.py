#!/usr/bin/env python3
"""
查看飞书表格的字段信息
"""
import requests

FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "REDACTED"
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    resp = requests.post(url, json=payload, timeout=10)
    return resp.json()['tenant_access_token']

def get_table_fields():
    token = get_feishu_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/fields"
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(url, headers=headers, timeout=30)
    result = resp.json()
    
    if result.get('code') == 0:
        fields = result['data']['items']
        print("飞书表格字段列表:\n")
        for field in fields:
            print(f"  字段名: {field['field_name']}")
            print(f"  字段ID: {field['field_id']}")
            print(f"  类型: {field['type']}")
            print()
    else:
        print(f"获取失败: {result}")

if __name__ == '__main__':
    get_table_fields()
