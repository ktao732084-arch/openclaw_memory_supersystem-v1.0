#!/usr/bin/env python3
"""
1. 自动找到最新的Sheet表格（Sheet开头的表格，按顺序取最后一个）
2. 给Sheet表格按单元ID分类排序（有单元ID的在前，没有的在后）
"""

import requests
from datetime import datetime

FEISHU_APP_ID = 'cli_a90737e0f5b81cd3'
FEISHU_APP_SECRET = 'REDACTED'
FEISHU_APP_TOKEN = 'FEiCbGEDHarzyUsPG8QcoLxwn7d'

def get_token():
    """获取飞书访问令牌"""
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    resp = requests.post(url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET})
    return resp.json()['tenant_access_token']

def find_latest_sheet(token):
    """找到最新的Sheet表格"""
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables'
    resp = requests.get(url, headers={'Authorization': f'Bearer {token}'})
    tables = resp.json()['data']['items']
    
    # 筛选出Sheet开头的表格
    sheet_tables = [t for t in tables if t['name'].startswith('Sheet')]
    
    if not sheet_tables:
        print("❌ 没有找到Sheet表格")
        return None
    
    # 取最后一个（最新的）
    latest_sheet = sheet_tables[-1]
    print(f"✓ 找到最新Sheet: {latest_sheet['name']} (ID: {latest_sheet['table_id']})")
    return latest_sheet

def get_all_records(token, table_id):
    """获取表格的所有记录（分页）"""
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records'
    headers = {'Authorization': f'Bearer {token}'}
    
    all_records = []
    page_token = None
    
    while True:
        params = {'page_size': 500}
        if page_token:
            params['page_token'] = page_token
        
        resp = requests.get(url, headers=headers, params=params)
        data = resp.json()
        
        if data.get('code') != 0:
            print(f"❌ 获取记录失败: {data}")
            break
        
        items = data.get('data', {}).get('items', [])
        all_records.extend(items)
        
        page_token = data.get('data', {}).get('page_token')
        if not page_token:
            break
    
    return all_records

def sort_records_by_unit_id(records):
    """按单元ID排序：有单元ID的在前，没有的在后"""
    with_unit_id = []
    without_unit_id = []
    
    for record in records:
        fields = record.get('fields', {})
        unit_id = fields.get('单元ID', '').strip()
        
        if unit_id:
            with_unit_id.append(record)
        else:
            without_unit_id.append(record)
    
    # 有单元ID的按单元ID排序
    with_unit_id.sort(key=lambda r: r.get('fields', {}).get('单元ID', ''))
    
    return with_unit_id + without_unit_id

def delete_all_records(token, table_id, record_ids):
    """批量删除记录"""
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records/batch_delete'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    # 每次最多删除500条
    batch_size = 500
    for i in range(0, len(record_ids), batch_size):
        batch = record_ids[i:i+batch_size]
        payload = {'records': batch}
        
        resp = requests.post(url, headers=headers, json=payload)
        data = resp.json()
        
        if data.get('code') == 0:
            print(f"  ✓ 删除 {len(batch)} 条记录")
        else:
            print(f"  ❌ 删除失败: {data}")

def create_records(token, table_id, records):
    """批量创建记录"""
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records/batch_create'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    # 每次最多创建500条
    batch_size = 500
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        
        # 只保留fields字段
        records_to_create = [{'fields': r.get('fields', {})} for r in batch]
        payload = {'records': records_to_create}
        
        resp = requests.post(url, headers=headers, json=payload)
        data = resp.json()
        
        if data.get('code') == 0:
            print(f"  ✓ 创建 {len(batch)} 条记录")
        else:
            print(f"  ❌ 创建失败: {data}")

def reorganize_sheet(token, table_id, table_name):
    """重新组织Sheet表格：按单元ID排序"""
    print(f"\n📋 重新组织 {table_name}...")
    
    # 1. 读取所有记录
    print("  📥 读取所有记录...")
    records = get_all_records(token, table_id)
    print(f"     找到 {len(records)} 条记录")
    
    # 2. 按单元ID排序
    print("  🔄 按单元ID排序...")
    sorted_records = sort_records_by_unit_id(records)
    
    with_unit = sum(1 for r in records if r.get('fields', {}).get('单元ID', '').strip())
    without_unit = len(records) - with_unit
    print(f"     有单元ID: {with_unit} 条")
    print(f"     无单元ID: {without_unit} 条")
    
    # 3. 删除所有记录
    print("  🗑️  删除旧记录...")
    record_ids = [r['record_id'] for r in records]
    delete_all_records(token, table_id, record_ids)
    
    # 4. 按新顺序创建记录
    print("  ✍️  按新顺序创建记录...")
    create_records(token, table_id, sorted_records)
    
    print(f"  ✅ {table_name} 重新组织完成！")

def main():
    print("🔄 开始处理Sheet表格...\n")
    
    # 获取token
    token = get_token()
    
    # 1. 找到最新的Sheet
    latest_sheet = find_latest_sheet(token)
    if not latest_sheet:
        return
    
    # 2. 重新组织这个Sheet
    reorganize_sheet(token, latest_sheet['table_id'], latest_sheet['name'])
    
    print("\n✅ 所有操作完成！")

if __name__ == '__main__':
    main()
