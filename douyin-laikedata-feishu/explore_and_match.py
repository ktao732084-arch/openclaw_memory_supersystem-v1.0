#!/usr/bin/env python3
"""
探查飞书表格并实现到店人数匹配
"""
import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

FEISHU_APP_ID = os.getenv('FEISHU_APP_ID')
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = os.getenv('FEISHU_APP_TOKEN')

# 表ID
TABLE_PROMOTION = "tbl1n1PC1aooYdKk"    # 投放数据表
TABLE_KEZI = "tblYgY0c0PRVqoqe"         # 客资数据表
TABLE_SHUNDING = "tblbIHSjDvlobJ4a"     # 顺鼎数据表

def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    response = requests.post(url, json=payload, timeout=10)
    return response.json()['tenant_access_token']

def list_fields(token, table_id):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/fields"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers, timeout=10)
    return response.json()

def get_all_records(token, table_id, filter_cond=None):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{table_id}/records/search"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    all_records = []
    page_token = None
    
    while True:
        payload = {"page_size": 500}
        if page_token:
            payload["page_token"] = page_token
        if filter_cond:
            payload["filter"] = filter_cond
        
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
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

def explore_table(token, table_id, table_name):
    print(f"\n{'='*80}")
    print(f"📊 探查表: {table_name} (ID: {table_id})")
    print(f"{'='*80}")
    
    # 字段列表
    fields_resp = list_fields(token, table_id)
    if fields_resp.get('code') == 0:
        fields = fields_resp['data']['items']
        print(f"\n字段列表 ({len(fields)} 个):")
        for field in fields:
            print(f"  - {field['field_name']} ({field['ui_type']})")
    else:
        print(f"❌ 获取字段失败: {fields_resp}")
        return
    
    # 示例数据
    print(f"\n示例数据 (前5条):")
    records = get_all_records(token, table_id)
    for i, record in enumerate(records[:5], 1):
        print(f"\n  记录 {i}:")
        for k, v in record['fields'].items():
            print(f"    {k}: {v}")
    
    print(f"\n总计: {len(records)} 条记录")
    return records

def normalize_phone(phone):
    """标准化手机号"""
    if not phone:
        return None
    phone_str = str(phone).strip()
    # 去掉 +86、-、空格等
    phone_str = phone_str.replace('+86', '').replace('-', '').replace(' ', '')
    # 只保留数字
    phone_str = ''.join([c for c in phone_str if c.isdigit()])
    # 11位手机号
    if len(phone_str) == 11 and phone_str.startswith('1'):
        return phone_str
    return None

def main():
    token = get_tenant_access_token()
    
    # 1. 探查所有表
    print("\n" + "="*80)
    print("第一步：探查所有相关表结构")
    print("="*80)
    
    shunding_records = explore_table(token, TABLE_SHUNDING, "顺鼎数据")
    kezi_records = explore_table(token, TABLE_KEZI, "客资数据")
    promotion_records = explore_table(token, TABLE_PROMOTION, "投放数据")
    
    # 2. 尝试匹配逻辑（先问清楚字段再写完整匹配）
    print("\n" + "="*80)
    print("第二步：确认匹配字段")
    print("="*80)
    print("\n请告诉我：")
    print("1. 顺鼎表里，手机号字段叫什么？")
    print("2. 顺鼎表里，有没有日期/到店时间字段？叫什么？")
    print("3. 客资表里，手机号字段是'手机号'吗？")
    print("4. 客资表里，'单元ID前15位'是用来关联投放数据的吗？")
    print("5. 投放表里，单元ID字段叫什么？'单元ID'还是其他？")

if __name__ == "__main__":
    main()
