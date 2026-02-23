#!/usr/bin/env python3
"""
查询飞书表格中昨天的数据
"""
import requests
from datetime import datetime, timedelta

FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    resp = requests.post(url, json=payload, timeout=10)
    return resp.json()['tenant_access_token']

def query_records(date_str):
    token = get_feishu_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/search"
    headers = {"Authorization": f"Bearer {token}"}
    
    payload = {
        "filter": {
            "conjunction": "and",
            "conditions": [{
                "field_name": "时间",
                "operator": "is",
                "value": [date_str]
            }]
        },
        "page_size": 500
    }
    
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    result = resp.json()
    
    if result.get('code') == 0:
        records = result['data']['items']
        return records
    else:
        print(f"查询失败: {result}")
        return []

def main():
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"查询日期: {yesterday}\n")
    
    records = query_records(yesterday)
    
    print(f"总记录数: {len(records)}\n")
    
    if records:
        print("记录明细:")
        accounts = {}
        for record in records:
            fields = record['fields']
            account_name = fields.get('文本', '未知')
            unit_name = fields.get('单元名称', '')
            cost = fields.get('消耗(元)', '0')
            convert = fields.get('转化数', '0')
            
            if account_name not in accounts:
                accounts[account_name] = []
            accounts[account_name].append({
                'unit': unit_name,
                'cost': cost,
                'convert': convert
            })
        
        print(f"\n账户汇总: {len(accounts)} 个账户\n")
        for account_name, items in accounts.items():
            print(f"  {account_name}:")
            print(f"    记录数: {len(items)}")
            for item in items:
                print(f"      - {item['unit']}: 消耗 {item['cost']}, 转化 {item['convert']}")

if __name__ == '__main__':
    main()
