#!/usr/bin/env python3
"""
从 Sheet2 迁移客资数据到"客资数据"表
"""
import requests
import time

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "REDACTED"
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
SHEET2_TABLE_ID = "tbl3Oyi6JYt3ZUIP"
KEZI_TABLE_ID = "tblYgY0c0PRVqoqe"

def get_feishu_token():
    """获取飞书访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    resp = requests.post(url, json=payload, timeout=10)
    return resp.json()['tenant_access_token']

def get_all_records(token, table_id):
    """获取表格的所有记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records"
    headers = {"Authorization": f"Bearer {token}"}
    
    all_records = []
    page_token = None
    
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        result = resp.json()
        
        if result.get('code') == 0:
            records = result['data']['items']
            all_records.extend(records)
            
            if not result['data'].get('has_more'):
                break
            page_token = result['data'].get('page_token')
        else:
            print(f"❌ 获取数据失败: {result}")
            break
    
    return all_records

def migrate_data():
    """迁移数据"""
    print("="*60)
    print("从 Sheet2 迁移客资数据")
    print("="*60)
    print()
    
    token = get_feishu_token()
    
    # 1. 获取 Sheet2 的所有数据
    print("1. 获取 Sheet2 的数据...")
    sheet2_records = get_all_records(token, SHEET2_TABLE_ID)
    print(f"   ✓ 获取到 {len(sheet2_records)} 条记录")
    print()
    
    # 2. 数据清洗和转换
    print("2. 数据清洗和转换...")
    
    clean_records = []
    for record in sheet2_records:
        fields = record['fields']
        
        # 只保留有手机号和单元ID的记录
        phone = fields.get('手机号', '')
        unit_id = fields.get('单元ID', '')
        
        if not phone or not unit_id:
            continue
        
        # 提取单元ID前15位
        unit_id_str = str(unit_id)
        unit_id_15 = unit_id_str[:15]
        
        # 提取日期（从线索创建时间）
        create_time = fields.get('线索创建时间', '')
        date_timestamp = None
        if create_time:
            # 格式: "2026-01-21 14:57:05"
            try:
                from datetime import datetime
                dt = datetime.strptime(create_time, '%Y-%m-%d %H:%M:%S')
                # 转换为毫秒时间戳
                date_timestamp = int(dt.timestamp() * 1000)
            except:
                continue
        
        if not date_timestamp:
            continue
        
        # 构建新记录
        new_record = {
            "fields": {
                "手机号": str(phone),
                "单元ID前15位": unit_id_15,
                "日期": date_timestamp,
                "客户姓名": fields.get('姓名', '')
            }
        }
        clean_records.append(new_record)
    
    print(f"   ✓ 清洗后: {len(clean_records)} 条有效记录")
    print()
    
    # 3. 去重（按手机号+单元ID+日期）
    print("3. 数据去重...")
    seen = set()
    unique_records = []
    
    for record in clean_records:
        fields = record['fields']
        key = (fields['手机号'], fields['单元ID前15位'], fields['日期'])
        
        if key not in seen:
            seen.add(key)
            unique_records.append(record)
    
    print(f"   ✓ 去重后: {len(unique_records)} 条唯一记录")
    print()
    
    # 4. 写入"客资数据"表
    print("4. 写入客资数据表...")
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{KEZI_TABLE_ID}/records/batch_create"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    batch_size = 500
    success_count = 0
    
    for i in range(0, len(unique_records), batch_size):
        batch = unique_records[i:i+batch_size]
        payload = {"records": batch}
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            result = resp.json()
            
            if result.get('code') == 0:
                success_count += len(batch)
                print(f"   ✓ 第 {i//batch_size + 1} 批写入成功: {len(batch)} 条")
            else:
                print(f"   ✗ 第 {i//batch_size + 1} 批失败: {result.get('msg')}")
        except Exception as e:
            print(f"   ✗ 写入失败: {e}")
        
        # 避免API限流
        time.sleep(0.5)
    
    print()
    print("="*60)
    print(f"迁移完成！成功写入 {success_count}/{len(unique_records)} 条")
    print("="*60)

if __name__ == '__main__':
    migrate_data()
