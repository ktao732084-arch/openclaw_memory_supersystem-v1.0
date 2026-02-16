#!/usr/bin/env python3
"""
查看飞书表格字段结构
"""
import requests
import json

FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "REDACTED"
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    resp = requests.post(url, json=payload, timeout=10)
    return resp.json()['tenant_access_token']

def get_table_fields():
    """获取表格字段"""
    token = get_token()
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/fields"
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(url, headers=headers, timeout=10)
    data = resp.json()
    
    if data.get('code') == 0:
        fields = data.get('data', {}).get('items', [])
        print(f"表格字段列表（共 {len(fields)} 个）：\n")
        for field in fields:
            print(f"- {field.get('field_name')} | 类型: {field.get('type')} | ID: {field.get('field_id')}")
        return fields
    else:
        print(f"获取失败: {data}")
        return []

if __name__ == '__main__':
    get_table_fields()
