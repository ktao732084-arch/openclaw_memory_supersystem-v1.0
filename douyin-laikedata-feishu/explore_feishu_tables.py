#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

load_dotenv()

FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = os.getenv('FEISHU_APP_TOKEN')

def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    response = requests.post(url, json=payload)
    return response.json()['tenant_access_token']

def list_tables(token):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    return response.json()

def list_fields(token, table_id):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/fields"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    return response.json()

def get_records(token, table_id, limit=10):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records?page_size={limit}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    return response.json()

def main():
    token = get_tenant_access_token()
    print("=" * 80)
    print("飞书多维表格 - 表列表")
    print("=" * 80)
    
    tables_resp = list_tables(token)
    if tables_resp.get('code') != 0:
        print(f"错误: {tables_resp}")
        return
    
    tables = tables_resp['data']['items']
    for table in tables:
        table_id = table['table_id']
        table_name = table['name']
        print(f"\n📊 表名: {table_name}")
        print(f"   表ID: {table_id}")
        
        print("\n   字段列表:")
        fields_resp = list_fields(token, table_id)
        if fields_resp.get('code') == 0:
            fields = fields_resp['data']['items']
            for field in fields:
                print(f"     - {field['field_name']} ({field['ui_type']})")
        
        print("\n   示例数据 (前3条):")
        records_resp = get_records(token, table_id, limit=3)
        if records_resp.get('code') == 0:
            records = records_resp['data'].get('items', [])
            for i, record in enumerate(records, 1):
                print(f"     记录 {i}: {record['fields']}")
        
        print("\n" + "-" * 80)

if __name__ == "__main__":
    main()
