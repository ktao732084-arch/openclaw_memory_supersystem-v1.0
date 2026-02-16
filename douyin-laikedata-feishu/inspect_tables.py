#!/usr/bin/env python3
"""查看飞书多维表格的所有表和字段结构"""

import requests
import json
import os

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "REDACTED"
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"

def get_tenant_access_token():
    """获取 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    response = requests.post(url, json=payload)
    data = response.json()
    if data.get("code") == 0:
        return data.get("tenant_access_token")
    else:
        print(f"❌ 获取token失败: {data}")
        return None

def list_tables(token):
    """获取所有数据表"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    
    if data.get("code") == 0:
        return data.get("data", {}).get("items", [])
    else:
        print(f"❌ 获取表格列表失败: {data}")
        return []

def get_table_fields(token, table_id):
    """获取表格的字段结构"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/fields"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    
    if data.get("code") == 0:
        return data.get("data", {}).get("items", [])
    else:
        print(f"❌ 获取字段失败: {data}")
        return []

def get_table_records(token, table_id, page_size=10):
    """获取表格的前几条记录（示例数据）"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    params = {
        "page_size": page_size
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    if data.get("code") == 0:
        return data.get("data", {}).get("items", [])
    else:
        print(f"❌ 获取记录失败: {data}")
        return []

def main():
    print("🔍 查看飞书多维表格结构\n")
    print("=" * 80)
    
    # 获取token
    token = get_tenant_access_token()
    if not token:
        return
    
    # 获取所有表
    tables = list_tables(token)
    print(f"\n📊 找到 {len(tables)} 个数据表:\n")
    
    for idx, table in enumerate(tables, 1):
        table_id = table.get("table_id")
        table_name = table.get("name")
        
        print(f"\n{'=' * 80}")
        print(f"📋 表 {idx}: {table_name}")
        print(f"   Table ID: {table_id}")
        print(f"{'=' * 80}")
        
        # 获取字段
        fields = get_table_fields(token, table_id)
        print(f"\n📝 字段列表 ({len(fields)} 个字段):")
        print("-" * 80)
        
        for field in fields:
            field_id = field.get("field_id")
            field_name = field.get("field_name")
            field_type = field.get("type")
            print(f"   • {field_name}")
            print(f"     - ID: {field_id}")
            print(f"     - 类型: {field_type}")
        
        # 获取示例数据
        records = get_table_records(token, table_id, page_size=3)
        print(f"\n📄 示例数据 (前 {len(records)} 条):")
        print("-" * 80)
        
        for i, record in enumerate(records, 1):
            print(f"\n   记录 {i}:")
            fields_data = record.get("fields", {})
            for field_name, value in fields_data.items():
                # 截断过长的值
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:50] + "..."
                print(f"     {field_name}: {value_str}")
        
        print("\n")

if __name__ == "__main__":
    main()
