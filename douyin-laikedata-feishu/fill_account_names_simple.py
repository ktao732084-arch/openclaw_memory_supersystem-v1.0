#!/usr/bin/env python3
"""
简单方案：根据日期填充账户名称
- 2月12日之前的数据：来自单账户（郑州天后医疗美容医院有限公司-XL）
- 2月12日及之后的数据：来自多账户，需要从API获取
"""

import requests
from account_names import ACCOUNT_NAMES

FEISHU_APP_ID = 'cli_a90737e0f5b81cd3'
FEISHU_APP_SECRET = 'REDACTED'
FEISHU_APP_TOKEN = 'FEiCbGEDHarzyUsPG8QcoLxwn7d'
TABLE_TOUFA = 'tbl1n1PC1aooYdKk'

# 单账户时期的账户名称
SINGLE_ACCOUNT_NAME = "郑州天后医疗美容医院有限公司-XL"

def get_token():
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    resp = requests.post(url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET})
    return resp.json()['tenant_access_token']

def get_all_records(token):
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
            break
        
        items = data.get('data', {}).get('items', [])
        all_records.extend(items)
        
        page_token = data.get('data', {}).get('page_token')
        if not page_token:
            break
    
    return all_records

def update_account_names(token, records):
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_TOUFA}/records/batch_update'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    updates = []
    
    for record in records:
        record_id = record.get('record_id')
        fields = record.get('fields', {})
        date = fields.get('时间', '')
        
        # 2月12日之前的数据，都是单账户
        if date < '2026-02-12':
            account_name = SINGLE_ACCOUNT_NAME
        else:
            # 2月12日及之后，暂时也用单账户名称
            # TODO: 从API获取真实账户名称
            account_name = SINGLE_ACCOUNT_NAME
        
        updates.append({
            'record_id': record_id,
            'fields': {
                '文本': account_name
            }
        })
    
    # 批量更新
    batch_size = 500
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        payload = {'records': batch}
        
        resp = requests.post(url, headers=headers, json=payload)
        data = resp.json()
        
        if data.get('code') == 0:
            print(f"✓ 更新 {len(batch)} 条记录")
        else:
            print(f"❌ 更新失败: {data}")

def main():
    print("🔄 填充账户名称到\"文本\"字段...\n")
    
    token = get_token()
    
    print("📥 读取投放数据...")
    records = get_all_records(token)
    print(f"   找到 {len(records)} 条记录\n")
    
    print("📝 更新账户名称...")
    update_account_names(token, records)
    
    print("\n✅ 完成！")

if __name__ == '__main__':
    main()
