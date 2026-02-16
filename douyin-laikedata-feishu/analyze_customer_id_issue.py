#!/usr/bin/env python3
"""
深度分析客户ID问题
"""
import requests
from collections import Counter, defaultdict

FEISHU_APP_ID = 'cli_a90737e0f5b81cd3'
FEISHU_APP_SECRET = 'REDACTED'
FEISHU_APP_TOKEN = 'FEiCbGEDHarzyUsPG8QcoLxwn7d'
TABLE_KEZI = 'tbl3Oyi6JYt3ZUIP'

def get_token():
    """获取飞书访问令牌"""
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    resp = requests.post(url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET})
    return resp.json()['tenant_access_token']

def get_all_records():
    """获取所有记录"""
    token = get_token()
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_KEZI}/records'
    headers = {'Authorization': f'Bearer {token}'}
    
    all_records = []
    page_token = None
    
    print("正在获取数据...")
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
        print(f"  已获取 {len(all_records)} 条记录...")
        
        page_token = data.get('data', {}).get('page_token')
        if not page_token:
            break
    
    return all_records

def analyze_customer_ids(records):
    """分析客户ID"""
    print("\n" + "=" * 60)
    print("客户ID深度分析")
    print("=" * 60)
    
    customer_ids = []
    phone_numbers = []
    customer_id_to_phones = defaultdict(set)
    customer_id_to_names = defaultdict(set)
    customer_id_to_records = defaultdict(list)
    
    for record in records:
        fields = record['fields']
        
        customer_id = fields.get('客户ID', '')
        phone = fields.get('手机号', '')
        name = fields.get('姓名', '')
        
        if customer_id:
            customer_ids.append(customer_id)
            customer_id_to_records[customer_id].append(record)
            
            if phone:
                customer_id_to_phones[customer_id].add(phone)
            if name:
                customer_id_to_names[customer_id].add(name)
        
        if phone:
            phone_numbers.append(phone)
    
    # 基础统计
    print(f"\n📊 基础统计：")
    print(f"  - 总记录数: {len(records)}")
    print(f"  - 有客户ID的记录: {len(customer_ids)}")
    print(f"  - 唯一客户ID数: {len(set(customer_ids))}")
    print(f"  - 有手机号的记录: {len(phone_numbers)}")
    print(f"  - 唯一手机号数: {len(set(phone_numbers))}")
    
    # 客户ID分布
    print(f"\n🔍 客户ID分布：")
    counter = Counter(customer_ids)
    print(f"  - 最常见的客户ID（前10）：")
    for cid, count in counter.most_common(10):
        print(f"    {cid}: {count}条记录")
    
    # 详细分析前3个客户ID
    print(f"\n📋 详细分析（前3个客户ID）：")
    for i, (cid, count) in enumerate(counter.most_common(3)):
        print(f"\n  客户ID: {cid}")
        print(f"  记录数: {count}")
        print(f"  不同手机号数: {len(customer_id_to_phones[cid])}")
        print(f"  不同姓名数: {len(customer_id_to_names[cid])}")
        
        # 显示手机号
        phones = list(customer_id_to_phones[cid])[:10]
        print(f"  手机号样本: {', '.join(phones)}")
        
        # 显示姓名
        names = list(customer_id_to_names[cid])[:10]
        print(f"  姓名样本: {', '.join(names)}")
    
    # 关键判断
    print(f"\n🎯 关键判断：")
    unique_customer_ids = len(set(customer_ids))
    unique_phones = len(set(phone_numbers))
    
    if unique_customer_ids == 1:
        print(f"  ⚠️ 所有记录的客户ID都相同！")
        print(f"  ⚠️ 这明显不正常，客户ID可能丢失或损坏")
        print(f"  ✅ 建议：使用手机号作为客户唯一标识")
    elif unique_customer_ids < 10:
        print(f"  ⚠️ 客户ID种类太少（只有{unique_customer_ids}个）")
        print(f"  ⚠️ 但有{unique_phones}个不同的手机号")
        print(f"  ⚠️ 客户ID可能有问题")
    else:
        print(f"  ✅ 客户ID看起来正常")
        print(f"  - {unique_customer_ids}个不同的客户ID")
        print(f"  - {unique_phones}个不同的手机号")
        
        # 分析一个客户有多少个手机号
        phones_per_customer = [len(phones) for phones in customer_id_to_phones.values()]
        avg_phones = sum(phones_per_customer) / len(phones_per_customer)
        max_phones = max(phones_per_customer)
        
        print(f"  - 平均每个客户有 {avg_phones:.2f} 个手机号")
        print(f"  - 最多的客户有 {max_phones} 个手机号")

if __name__ == '__main__':
    records = get_all_records()
    analyze_customer_ids(records)
