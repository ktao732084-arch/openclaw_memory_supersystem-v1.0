#!/usr/bin/env python3
"""查看指定表格的字段和示例数据"""

import requests
import json

FEISHU_APP_ID = 'cli_a90737e0f5b81cd3'
FEISHU_APP_SECRET = 'REDACTED'
FEISHU_APP_TOKEN = 'FEiCbGEDHarzyUsPG8QcoLxwn7d'

def get_token():
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    resp = requests.post(url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET})
    return resp.json()['tenant_access_token']

def view_table(token, table_id, table_name):
    print(f"\n{'='*80}")
    print(f"📋 {table_name} (ID: {table_id})")
    print(f"{'='*80}")
    
    # 获取字段
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/fields'
    resp = requests.get(url, headers={'Authorization': f'Bearer {token}'})
    fields = resp.json()['data']['items']
    
    print(f"\n📝 字段列表 ({len(fields)} 个):")
    print("-" * 80)
    for field in fields:
        print(f"  • {field['field_name']:<20} (类型: {field['type']}, ID: {field['field_id']})")
    
    # 获取示例数据
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records'
    resp = requests.get(url, headers={'Authorization': f'Bearer {token}'}, params={'page_size': 3})
    records = resp.json()['data']['items']
    
    print(f"\n📄 示例数据 (前 {len(records)} 条):")
    print("-" * 80)
    for i, record in enumerate(records, 1):
        print(f"\n  记录 {i}:")
        for field_name, value in record['fields'].items():
            value_str = str(value)
            if len(value_str) > 60:
                value_str = value_str[:60] + "..."
            print(f"    {field_name}: {value_str}")

def main():
    token = get_token()
    
    # 查看"数据表"（投放数据）
    view_table(token, 'tbl1n1PC1aooYdKk', '数据表（投放数据）')
    
    # 查看"Sheet1"（客资数据）
    view_table(token, 'tblg2QsWDaKO4sYu', 'Sheet1（客资数据）')

if __name__ == '__main__':
    main()
