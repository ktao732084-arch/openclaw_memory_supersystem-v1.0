#!/usr/bin/env python3
"""
从Excel中提取单元ID → 账户ID → 账户名称的映射
然后更新投放数据表的"文本"字段
"""

import zipfile
import xml.etree.ElementTree as ET
import requests

EXCEL_PATH = '/root/单元投放_账户列表_64763_2026_02_13 00_57_23.xlsx'

FEISHU_APP_ID = 'cli_a90737e0f5b81cd3'
FEISHU_APP_SECRET = 'REDACTED'
FEISHU_APP_TOKEN = 'FEiCbGEDHarzyUsPG8QcoLxwn7d'
TABLE_TOUFA = 'tbl1n1PC1aooYdKk'

def extract_unit_to_account_mapping():
    """从Excel提取单元ID → 账户ID → 账户名称的映射"""
    
    # 打开Excel（实际是zip文件）
    with zipfile.ZipFile(EXCEL_PATH, 'r') as zip_ref:
        # 读取共享字符串表
        shared_strings = []
        try:
            with zip_ref.open('xl/sharedStrings.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                ns = {'': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                for si in root.findall('.//t', ns):
                    shared_strings.append(si.text or '')
        except:
            pass
        
        # 读取第一个工作表
        with zip_ref.open('xl/worksheets/sheet1.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            ns = {'': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            
            # 读取所有行
            rows = []
            for row in root.findall('.//row', ns):
                row_data = []
                for cell in row.findall('.//c', ns):
                    cell_type = cell.get('t')
                    value_elem = cell.find('.//v', ns)
                    
                    if value_elem is not None:
                        value = value_elem.text
                        # 如果是共享字符串类型
                        if cell_type == 's':
                            idx = int(value)
                            if idx < len(shared_strings):
                                value = shared_strings[idx]
                        row_data.append(value)
                    else:
                        row_data.append('')
                
                if row_data:
                    rows.append(row_data)
    
    # 找到表头
    header = rows[0] if rows else []
    print(f"表头: {header[:10]}")
    
    # 找到关键列的索引
    try:
        unit_id_idx = header.index('单元id')
        account_id_idx = header.index('账户id')
        account_name_idx = header.index('账户')
    except ValueError as e:
        print(f"❌ 找不到必要的列: {e}")
        return {}
    
    # 提取映射关系
    unit_to_account = {}
    
    for row in rows[1:]:  # 跳过表头
        if len(row) > max(unit_id_idx, account_id_idx, account_name_idx):
            unit_id = row[unit_id_idx].strip()
            account_id = row[account_id_idx].strip()
            account_name = row[account_name_idx].strip()
            
            if unit_id and account_name:
                unit_to_account[unit_id] = account_name
    
    return unit_to_account

def get_token():
    """获取飞书访问令牌"""
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    resp = requests.post(url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET})
    return resp.json()['tenant_access_token']

def get_all_records(token):
    """获取所有投放记录"""
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

def update_account_names(token, records, unit_to_account):
    """更新投放数据表的"文本"字段为账户名称"""
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_TOUFA}/records/batch_update'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    updates = []
    matched = 0
    not_matched = 0
    
    for record in records:
        record_id = record.get('record_id')
        fields = record.get('fields', {})
        unit_id = fields.get('单元ID', '').strip()
        
        if not unit_id:
            continue
        
        # 查找账户名称
        account_name = unit_to_account.get(unit_id)
        
        if account_name:
            matched += 1
            updates.append({
                'record_id': record_id,
                'fields': {
                    '文本': account_name
                }
            })
        else:
            not_matched += 1
    
    print(f"\n匹配结果:")
    print(f"  ✓ 匹配成功: {matched} 条")
    print(f"  ✗ 未匹配: {not_matched} 条")
    
    if not updates:
        print("\n没有需要更新的记录")
        return
    
    # 批量更新
    batch_size = 500
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        payload = {'records': batch}
        
        resp = requests.post(url, headers=headers, json=payload)
        data = resp.json()
        
        if data.get('code') == 0:
            print(f"  ✓ 更新 {len(batch)} 条记录")
        else:
            print(f"  ❌ 更新失败: {data}")

def main():
    print("🔄 开始更新账户名称...\n")
    
    # 1. 从Excel提取映射
    print("📥 从Excel提取单元ID → 账户名称映射...")
    unit_to_account = extract_unit_to_account_mapping()
    print(f"   找到 {len(unit_to_account)} 个单元ID的映射")
    
    if not unit_to_account:
        print("❌ 没有提取到映射数据")
        return
    
    # 显示前5个映射
    print("\n示例映射（前5个）:")
    for i, (unit_id, account_name) in enumerate(list(unit_to_account.items())[:5], 1):
        print(f"  {i}. 单元ID {unit_id} → {account_name}")
    
    # 2. 获取token
    token = get_token()
    
    # 3. 读取投放数据
    print("\n📥 读取投放数据...")
    records = get_all_records(token)
    print(f"   找到 {len(records)} 条投放记录")
    
    # 4. 更新账户名称
    print("\n📝 更新账户名称到\"文本\"字段...")
    update_account_names(token, records, unit_to_account)
    
    print("\n✅ 账户名称更新完成！")

if __name__ == '__main__':
    main()
