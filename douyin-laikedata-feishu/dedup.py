#!/usr/bin/env python3
"""
飞书数据去重工具
"""
import requests
import json
from datetime import datetime

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "REDACTED"
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def get_feishu_token():
    """获取飞书 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    
    if resp.status_code == 200:
        data = resp.json()
        if data.get('code') == 0:
            return data.get('tenant_access_token')
    return None

def get_existing_records(token, date_str=None):
    """获取飞书中已存在的记录"""
    print(f"📋 查询飞书中的现有记录...")
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/search"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    all_records = []
    page_token = None
    
    while True:
        payload = {
            "page_size": 500
        }
        
        # 如果指定了日期，添加过滤条件
        if date_str:
            payload["filter"] = {
                "conjunction": "and",
                "conditions": [
                    {
                        "field_name": "时间",
                        "operator": "is",
                        "value": [date_str]
                    }
                ]
            }
        
        if page_token:
            payload["page_token"] = page_token
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            result = resp.json()
            
            if result.get('code') == 0:
                data = result.get('data', {})
                items = data.get('items', [])
                all_records.extend(items)
                
                # 检查是否还有下一页
                if not data.get('has_more'):
                    break
                
                page_token = data.get('page_token')
            else:
                print(f"❌ 查询失败: {result.get('msg')}")
                break
                
        except Exception as e:
            print(f"❌ 查询异常: {e}")
            break
    
    print(f"✓ 找到 {len(all_records)} 条现有记录")
    return all_records

def build_record_key(record):
    """构建记录的唯一键（日期 + 单元ID）"""
    fields = record.get('fields', {})
    
    # 处理字段值（可能是字典或字符串）
    date_field = fields.get('时间', '')
    unit_id_field = fields.get('单元ID', '')
    
    # 提取实际值
    if isinstance(date_field, dict):
        date = date_field.get('text', '')
    else:
        date = str(date_field)
    
    if isinstance(unit_id_field, dict):
        unit_id = unit_id_field.get('text', '')
    else:
        unit_id = str(unit_id_field)
    
    return f"{date}_{unit_id}"

def filter_duplicates(new_data, existing_records):
    """过滤重复数据"""
    print(f"\n🔍 检查重复数据...")
    
    # 构建已存在记录的键集合
    existing_keys = set()
    for record in existing_records:
        key = build_record_key(record)
        if key:
            existing_keys.add(key)
    
    print(f"   已存在的记录键: {len(existing_keys)} 个")
    
    # 过滤新数据
    unique_data = []
    duplicate_count = 0
    
    for item in new_data:
        date = item.get('stat_time_day', '')
        unit_id = str(item.get('promotion_id', ''))
        key = f"{date}_{unit_id}"
        
        if key not in existing_keys:
            unique_data.append(item)
        else:
            duplicate_count += 1
    
    print(f"   新数据: {len(new_data)} 条")
    print(f"   重复: {duplicate_count} 条")
    print(f"   需要写入: {len(unique_data)} 条")
    
    return unique_data

def delete_records_by_date(token, date_str):
    """删除指定日期的所有记录"""
    print(f"\n🗑️  删除 {date_str} 的旧记录...")
    
    # 先查询该日期的记录
    records = get_existing_records(token, date_str)
    
    if not records:
        print("   没有需要删除的记录")
        return True
    
    # 批量删除
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/batch_delete"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 提取记录ID
    record_ids = [r.get('record_id') for r in records if r.get('record_id')]
    
    # 分批删除（每批最多500条）
    batch_size = 500
    deleted_count = 0
    
    for i in range(0, len(record_ids), batch_size):
        batch = record_ids[i:i+batch_size]
        payload = {"records": batch}
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            result = resp.json()
            
            if result.get('code') == 0:
                deleted_count += len(batch)
                print(f"   ✓ 删除第 {i//batch_size + 1} 批: {len(batch)} 条")
            else:
                print(f"   ❌ 删除失败: {result.get('msg')}")
        except Exception as e:
            print(f"   ❌ 删除异常: {e}")
    
    print(f"   ✅ 共删除 {deleted_count} 条记录")
    return deleted_count > 0

def check_duplicates_for_date(date_str):
    """检查指定日期是否有重复数据"""
    print("="*60)
    print(f"检查 {date_str} 的重复数据")
    print("="*60 + "\n")
    
    token = get_feishu_token()
    if not token:
        print("❌ 无法获取飞书 token")
        return
    
    records = get_existing_records(token, date_str)
    
    if not records:
        print(f"\n✅ {date_str} 没有数据")
        return
    
    # 统计重复
    key_count = {}
    for record in records:
        key = build_record_key(record)
        if key:
            key_count[key] = key_count.get(key, 0) + 1
    
    # 找出重复的
    duplicates = {k: v for k, v in key_count.items() if v > 1}
    
    if duplicates:
        print(f"\n⚠️  发现重复数据:")
        for key, count in duplicates.items():
            print(f"   {key}: {count} 条")
        
        print(f"\n💡 建议运行去重:")
        print(f"   python3 dedup.py clean {date_str}")
    else:
        print(f"\n✅ {date_str} 没有重复数据")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 dedup.py check <日期>     # 检查指定日期的重复")
        print("  python3 dedup.py clean <日期>     # 删除指定日期的所有记录")
        print("\n示例:")
        print("  python3 dedup.py check 2026-02-11")
        print("  python3 dedup.py clean 2026-02-11")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "check":
        if len(sys.argv) < 3:
            # 默认检查昨天
            from datetime import timedelta
            date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            date_str = sys.argv[2]
        
        check_duplicates_for_date(date_str)
    
    elif command == "clean":
        if len(sys.argv) < 3:
            print("❌ 请指定日期")
            sys.exit(1)
        
        date_str = sys.argv[2]
        
        print("="*60)
        print(f"清理 {date_str} 的数据")
        print("="*60 + "\n")
        
        confirm = input(f"⚠️  确认删除 {date_str} 的所有记录？(yes/no): ")
        
        if confirm.lower() == 'yes':
            token = get_feishu_token()
            if token:
                delete_records_by_date(token, date_str)
        else:
            print("已取消")
