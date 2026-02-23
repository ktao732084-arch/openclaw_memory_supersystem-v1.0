#!/usr/bin/env python3
"""
清理数据表：
1. 删除空白记录（没有单元ID的）
2. 删除重复记录（相同日期+单元ID的）
"""

import requests
from collections import defaultdict

FEISHU_APP_ID = 'cli_a90737e0f5b81cd3'
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = 'FEiCbGEDHarzyUsPG8QcoLxwn7d'
TABLE_TOUFA = 'tbl1n1PC1aooYdKk'  # 数据表（投放数据）

def get_token():
    """获取飞书访问令牌"""
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    resp = requests.post(url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET})
    return resp.json()['tenant_access_token']

def get_all_records(token):
    """获取所有记录"""
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_TOUFA}/records'
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

def find_duplicates_and_blanks(records):
    """找出重复记录和空白记录"""
    blank_records = []  # 空白记录（没有单元ID）
    duplicate_records = []  # 重复记录
    seen = {}  # 用于检测重复：key=(日期, 单元ID), value=record_id
    
    for record in records:
        record_id = record.get('record_id')
        fields = record.get('fields', {})
        
        unit_id = fields.get('单元ID', '').strip()
        date = fields.get('时间', '').strip()
        
        # 检查空白记录
        if not unit_id:
            blank_records.append({
                'record_id': record_id,
                'date': date,
                'reason': '没有单元ID'
            })
            continue
        
        # 检查重复记录
        key = (date, unit_id)
        if key in seen:
            duplicate_records.append({
                'record_id': record_id,
                'date': date,
                'unit_id': unit_id,
                'duplicate_of': seen[key]
            })
        else:
            seen[key] = record_id
    
    return blank_records, duplicate_records

def delete_records(token, record_ids):
    """批量删除记录"""
    if not record_ids:
        return
    
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_TOUFA}/records/batch_delete'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    # 每次最多删除500条
    batch_size = 500
    total_deleted = 0
    
    for i in range(0, len(record_ids), batch_size):
        batch = record_ids[i:i+batch_size]
        payload = {'records': batch}
        
        resp = requests.post(url, headers=headers, json=payload)
        data = resp.json()
        
        if data.get('code') == 0:
            total_deleted += len(batch)
            print(f"  ✓ 删除 {len(batch)} 条记录")
        else:
            print(f"  ❌ 删除失败: {data}")
    
    return total_deleted

def main():
    print("🔍 开始检查数据表...\n")
    
    # 获取token
    token = get_token()
    
    # 读取所有记录
    print("📥 读取所有记录...")
    records = get_all_records(token)
    print(f"   找到 {len(records)} 条记录\n")
    
    # 查找空白和重复记录
    print("🔍 检查空白和重复记录...")
    blank_records, duplicate_records = find_duplicates_and_blanks(records)
    
    print(f"   空白记录: {len(blank_records)} 条")
    print(f"   重复记录: {len(duplicate_records)} 条\n")
    
    # 显示详情
    if blank_records:
        print("📋 空白记录详情（前10条）:")
        print("-" * 80)
        for i, r in enumerate(blank_records[:10], 1):
            print(f"   {i}. 日期: {r['date'] or '(空)'}, 原因: {r['reason']}")
        if len(blank_records) > 10:
            print(f"   ... 还有 {len(blank_records) - 10} 条")
        print()
    
    if duplicate_records:
        print("📋 重复记录详情（前10条）:")
        print("-" * 80)
        for i, r in enumerate(duplicate_records[:10], 1):
            print(f"   {i}. 日期: {r['date']}, 单元ID: {r['unit_id']}")
        if len(duplicate_records) > 10:
            print(f"   ... 还有 {len(duplicate_records) - 10} 条")
        print()
    
    # 询问是否删除
    total_to_delete = len(blank_records) + len(duplicate_records)
    
    if total_to_delete == 0:
        print("✅ 数据表很干净，没有需要清理的记录！")
        return
    
    print(f"⚠️  准备删除 {total_to_delete} 条记录")
    print(f"   - 空白记录: {len(blank_records)} 条")
    print(f"   - 重复记录: {len(duplicate_records)} 条\n")
    
    # 自动执行删除
    print("🗑️  开始删除...")
    
    # 删除空白记录
    if blank_records:
        print("\n  删除空白记录:")
        blank_ids = [r['record_id'] for r in blank_records]
        delete_records(token, blank_ids)
    
    # 删除重复记录
    if duplicate_records:
        print("\n  删除重复记录:")
        duplicate_ids = [r['record_id'] for r in duplicate_records]
        delete_records(token, duplicate_ids)
    
    print(f"\n✅ 清理完成！共删除 {total_to_delete} 条记录")
    print(f"   剩余记录: {len(records) - total_to_delete} 条")

if __name__ == '__main__':
    main()
