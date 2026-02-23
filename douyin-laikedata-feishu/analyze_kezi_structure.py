#!/usr/bin/env python3
"""
分析飞书客资表格的结构和数据
"""
import requests
from collections import Counter

# 飞书配置
FEISHU_APP_ID = 'cli_a90737e0f5b81cd3'
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = 'FEiCbGEDHarzyUsPG8QcoLxwn7d'
TABLE_KEZI = 'tbl3Oyi6JYt3ZUIP'  # Sheet2（客资数据）

def get_token():
    """获取飞书访问令牌"""
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    resp = requests.post(url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET})
    return resp.json()['tenant_access_token']

def list_tables():
    """列出所有表格"""
    token = get_token()
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables'
    headers = {'Authorization': f'Bearer {token}'}
    
    resp = requests.get(url, headers=headers)
    data = resp.json()
    
    if data.get('code') != 0:
        print(f"❌ 获取表格列表失败: {data}")
        return []
    
    print("📋 表格列表：")
    tables = []
    for table in data.get('data', {}).get('items', []):
        print(f"  - {table['name']} (ID: {table['table_id']})")
        tables.append({
            'name': table['name'],
            'table_id': table['table_id']
        })
    
    return tables

def get_table_fields(table_id):
    """获取表格字段"""
    token = get_token()
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/fields'
    headers = {'Authorization': f'Bearer {token}'}
    
    resp = requests.get(url, headers=headers)
    data = resp.json()
    
    if data.get('code') != 0:
        print(f"❌ 获取字段失败: {data}")
        return []
    
    print(f"\n📊 字段列表：")
    fields = []
    for field in data.get('data', {}).get('items', []):
        field_info = {
            'name': field['field_name'],
            'id': field['field_id'],
            'type': field['type']
        }
        fields.append(field_info)
        print(f"  - {field['field_name']} ({field['type']}) [ID: {field['field_id']}]")
    
    return fields

def get_all_records(token, table_id, limit=1000):
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
        
        if len(all_records) >= limit:
            all_records = all_records[:limit]
            break
        
        page_token = data.get('data', {}).get('page_token')
        if not page_token:
            break
    
    return all_records

def analyze_records(table_id, fields, limit=1000):
    """分析记录数据"""
    token = get_token()
    records = get_all_records(token, table_id, limit)
    
    print(f"\n📈 数据分析（共 {len(records)} 条记录）：")
    
    # 找到关键字段 - 使用字段名直接匹配
    field_map = {f['name']: f['id'] for f in fields}
    
    # 提取数据
    customer_ids = []
    phone_numbers = []
    unit_ids = []
    dates = []
    unit_names = []
    
    for record in records:
        fields_data = record['fields']
        
        # 客户ID
        if '客户ID' in field_map and field_map['客户ID'] in fields_data:
            customer_ids.append(fields_data[field_map['客户ID']])
        
        # 手机号
        if '手机号' in field_map and field_map['手机号'] in fields_data:
            phone_numbers.append(fields_data[field_map['手机号']])
        
        # 单元ID
        if '单元ID' in field_map and field_map['单元ID'] in fields_data:
            unit_ids.append(fields_data[field_map['单元ID']])
        
        # 线索创建时间
        if '线索创建时间' in field_map and field_map['线索创建时间'] in fields_data:
            dates.append(fields_data[field_map['线索创建时间']])
        
        # 单元名称
        if '单元名称' in field_map and field_map['单元名称'] in fields_data:
            unit_names.append(fields_data[field_map['单元名称']])
    
    # 统计分析
    print(f"\n🔍 客户ID分析：")
    if customer_ids:
        valid_customer_ids = [c for c in customer_ids if c]
        print(f"  - 总记录数: {len(customer_ids)}")
        print(f"  - 有客户ID: {len(valid_customer_ids)}")
        print(f"  - 唯一客户ID数: {len(set(valid_customer_ids))}")
        print(f"  - 重复率: {(1 - len(set(valid_customer_ids)) / len(valid_customer_ids)) * 100:.2f}%")
        
        # 找出重复最多的客户ID
        counter = Counter(valid_customer_ids)
        most_common = counter.most_common(10)
        print(f"\n  重复最多的客户ID（前10）：")
        for cid, count in most_common:
            if count > 1:
                print(f"    - {cid}: {count}次")
    else:
        print("  ⚠️ 未找到客户ID数据")
    
    print(f"\n📱 手机号分析：")
    if phone_numbers:
        valid_phones = [p for p in phone_numbers if p]
        print(f"  - 总记录数: {len(phone_numbers)}")
        print(f"  - 有手机号: {len(valid_phones)}")
        print(f"  - 唯一手机号数: {len(set(valid_phones))}")
        if valid_phones:
            print(f"  - 手机号重复率: {(1 - len(set(valid_phones)) / len(valid_phones)) * 100:.2f}%")
            
            # 找出重复最多的手机号
            counter = Counter(valid_phones)
            most_common = counter.most_common(10)
            print(f"\n  重复最多的手机号（前10）：")
            for phone, count in most_common:
                if count > 1:
                    print(f"    - {phone}: {count}次")
    else:
        print("  ⚠️ 未找到手机号数据")
    
    print(f"\n🎯 单元ID分析：")
    if unit_ids:
        valid_units = [u for u in unit_ids if u]
        print(f"  - 总记录数: {len(unit_ids)}")
        print(f"  - 有单元ID: {len(valid_units)}")
        print(f"  - 唯一单元ID数: {len(set(valid_units))}")
    else:
        print("  ⚠️ 未找到单元ID数据")
    
    print(f"\n📅 线索创建时间分析：")
    if dates:
        valid_dates = [d for d in dates if d]
        print(f"  - 总记录数: {len(dates)}")
        print(f"  - 有时间: {len(valid_dates)}")
        if valid_dates:
            # 转换时间戳为日期
            from datetime import datetime
            date_strs = []
            for ts in valid_dates:
                try:
                    dt = datetime.fromtimestamp(int(ts) / 1000)
                    date_strs.append(dt.strftime('%Y-%m-%d'))
                except:
                    pass
            if date_strs:
                print(f"  - 唯一日期数: {len(set(date_strs))}")
                print(f"  - 日期范围: {min(date_strs)} 至 {max(date_strs)}")
    else:
        print("  ⚠️ 未找到时间数据")
    
    # 打印几条示例记录
    print(f"\n📝 示例记录（前5条）：")
    for i, record in enumerate(records[:5]):
        print(f"\n  记录 {i+1}:")
        for field_name in ['客户ID', '手机号', '单元ID', '单元名称', '线索创建时间']:
            if field_name in field_map:
                field_id = field_map[field_name]
                if field_id in record['fields']:
                    value = record['fields'][field_id]
                    # 时间戳转换
                    if field_name == '线索创建时间' and value:
                        try:
                            from datetime import datetime
                            dt = datetime.fromtimestamp(int(value) / 1000)
                            value = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            pass
                    # 截断长文本
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"    {field_name}: {value}")



def main():
    print("=" * 60)
    print("飞书客资表格结构分析")
    print("=" * 60)
    
    # 直接分析客资表格
    print(f"\n分析表格: Sheet2 (客资数据)")
    print(f"Table ID: {TABLE_KEZI}")
    print("=" * 60)
    
    # 获取字段
    fields = get_table_fields(TABLE_KEZI)
    
    # 分析数据
    analyze_records(TABLE_KEZI, fields, limit=2000)

if __name__ == '__main__':
    main()
