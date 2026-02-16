#!/usr/bin/env python3
"""
飞书多维表格去重脚本
根据"单元ID"和"时间"字段去重，保留最早创建的记录
"""
import requests
import json
from datetime import datetime

# 配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "REDACTED"
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def get_feishu_token():
    """获取飞书 Token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    response = requests.post(url, json=payload, timeout=10)
    return response.json()["tenant_access_token"]

def get_field_value(field_data):
    """提取字段值（处理飞书的复杂字段格式）"""
    if isinstance(field_data, list) and len(field_data) > 0:
        if isinstance(field_data[0], dict) and 'text' in field_data[0]:
            return field_data[0]['text']
    return str(field_data) if field_data else ''

def get_all_records(token, date_filter=None):
    """获取所有记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/search"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    payload = {"page_size": 500}
    
    if date_filter:
        payload["filter"] = {
            "conjunction": "and",
            "conditions": [
                {
                    "field_name": "时间",
                    "operator": "is",
                    "value": [date_filter]
                }
            ]
        }
    
    all_records = []
    has_more = True
    page_token = None
    
    while has_more:
        if page_token:
            payload["page_token"] = page_token
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        result = response.json()
        
        if result.get('code') == 0:
            items = result.get('data', {}).get('items', [])
            all_records.extend(items)
            
            has_more = result.get('data', {}).get('has_more', False)
            page_token = result.get('data', {}).get('page_token')
        else:
            print(f"❌ 获取记录失败: {result}")
            break
    
    return all_records

def find_duplicates(records):
    """查找重复记录"""
    seen = {}
    duplicates = []
    
    for record in records:
        record_id = record['record_id']
        fields = record.get('fields', {})
        
        # 提取关键字段
        unit_id = get_field_value(fields.get('单元ID', ''))
        date = get_field_value(fields.get('时间', ''))
        
        # 生成唯一键
        key = f"{unit_id}_{date}"
        
        if key in seen:
            # 发现重复，保留最早的记录
            duplicates.append(record_id)
        else:
            seen[key] = record_id
    
    return duplicates

def delete_records(token, record_ids):
    """批量删除记录"""
    if not record_ids:
        return True
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_delete"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # 飞书API限制每次最多删除500条
    batch_size = 500
    total_deleted = 0
    
    for i in range(0, len(record_ids), batch_size):
        batch = record_ids[i:i+batch_size]
        payload = {"records": batch}
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        result = response.json()
        
        if result.get('code') == 0:
            total_deleted += len(batch)
            print(f"  ✅ 已删除 {len(batch)} 条记录（总计: {total_deleted}/{len(record_ids)}）")
        else:
            print(f"  ❌ 删除失败: {result}")
            return False
    
    return True

def main():
    import sys
    
    print("=" * 60)
    print("飞书多维表格去重工具")
    print("=" * 60)
    
    # 获取参数
    date_filter = sys.argv[1] if len(sys.argv) > 1 else None
    dry_run = "--dry-run" in sys.argv
    
    if date_filter:
        print(f"\n筛选日期: {date_filter}")
    else:
        print(f"\n处理所有记录")
    
    if dry_run:
        print("⚠️  试运行模式（不会实际删除）")
    
    # 1. 获取飞书 Token
    print("\n步骤1: 获取飞书 Token...")
    token = get_feishu_token()
    print("✅ Token 获取成功")
    
    # 2. 获取所有记录
    print(f"\n步骤2: 获取记录...")
    records = get_all_records(token, date_filter)
    print(f"✅ 找到 {len(records)} 条记录")
    
    if not records:
        print("\n⚠️  没有记录需要处理")
        return
    
    # 3. 查找重复
    print(f"\n步骤3: 查找重复记录...")
    duplicates = find_duplicates(records)
    print(f"✅ 发现 {len(duplicates)} 条重复记录")
    
    if not duplicates:
        print("\n✅ 没有重复记录，无需清理")
        return
    
    # 4. 显示统计
    print(f"\n统计信息:")
    print(f"  - 总记录数: {len(records)}")
    print(f"  - 重复记录: {len(duplicates)}")
    print(f"  - 保留记录: {len(records) - len(duplicates)}")
    
    # 5. 删除重复记录
    if dry_run:
        print(f"\n⚠️  试运行模式，跳过删除")
        print(f"   如需实际删除，请运行: python3 dedup_feishu.py {date_filter or ''}")
    else:
        print(f"\n步骤4: 删除重复记录...")
        
        # 确认
        confirm = input(f"⚠️  确认删除 {len(duplicates)} 条重复记录？(yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ 已取消")
            return
        
        success = delete_records(token, duplicates)
        
        if success:
            print(f"\n✅ 去重完成！")
            print(f"   删除了 {len(duplicates)} 条重复记录")
            print(f"   保留了 {len(records) - len(duplicates)} 条唯一记录")
        else:
            print(f"\n❌ 去重失败")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
