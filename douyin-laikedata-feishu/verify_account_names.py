#!/usr/bin/env python3
"""
验证账户名称是否正确写入
"""
import requests

FEISHU_APP_ID = 'cli_a90737e0f5b81cd3'
FEISHU_APP_SECRET = 'REDACTED'
FEISHU_APP_TOKEN = 'FEiCbGEDHarzyUsPG8QcoLxwn7d'
TABLE_TOUFA = 'tbl1n1PC1aooYdKk'

def get_token():
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    resp = requests.post(url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET})
    return resp.json()['tenant_access_token']

def check_recent_records():
    """检查最近写入的记录"""
    token = get_token()
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_TOUFA}/records'
    headers = {'Authorization': f'Bearer {token}'}
    
    # 获取最近的记录
    params = {
        'page_size': 10,
        'filter': '{"conjunction":"and","conditions":[{"field_name":"时间","operator":"is","value":["2026-02-12"]}]}'
    }
    
    resp = requests.get(url, headers=headers, params=params)
    data = resp.json()
    
    if data.get('code') == 0:
        items = data.get('data', {}).get('items', [])
        print(f"找到 {len(items)} 条 2026-02-12 的记录\n")
        
        print("账户名称验证（前10条）：\n")
        for i, item in enumerate(items, 1):
            fields = item.get('fields', {})
            account_name = fields.get('文本', '')
            unit_name = fields.get('单元名称', '')
            cost = fields.get('消耗(元)', '')
            
            print(f"{i}. 账户: {account_name}")
            print(f"   单元: {unit_name}")
            print(f"   消耗: {cost} 元\n")
    else:
        print(f"❌ 获取失败: {data}")

if __name__ == '__main__':
    check_recent_records()
