#!/usr/bin/env python3
"""
统计飞书表格中昨天各账户的数据
"""
import requests
from datetime import datetime, timedelta
from collections import defaultdict

FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "REDACTED"
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
        return result['data']['items']
    else:
        print(f"查询失败: {result}")
        return []

def main():
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"查询日期: {yesterday}\n")
    
    records = query_records(yesterday)
    print(f"总记录数: {len(records)}\n")
    
    # 按账户统计
    accounts = defaultdict(lambda: {'count': 0, 'cost': 0, 'convert': 0})
    
    for record in records:
        fields = record['fields']
        
        # 提取账户名称
        account_name = "未知"
        if '账户名称' in fields:
            account_field = fields['账户名称']
            if isinstance(account_field, list) and len(account_field) > 0:
                account_name = account_field[0].get('text', '未知')
        
        # 提取消耗和转化
        cost = 0
        if '消耗(元)' in fields:
            cost_field = fields['消耗(元)']
            if isinstance(cost_field, list) and len(cost_field) > 0:
                try:
                    cost = float(cost_field[0].get('text', '0'))
                except:
                    cost = 0
        
        convert = 0
        if '转化数' in fields:
            convert_field = fields['转化数']
            if isinstance(convert_field, list) and len(convert_field) > 0:
                try:
                    convert = int(convert_field[0].get('text', '0'))
                except:
                    convert = 0
        
        accounts[account_name]['count'] += 1
        accounts[account_name]['cost'] += cost
        accounts[account_name]['convert'] += convert
    
    print(f"账户汇总: {len(accounts)} 个账户\n")
    
    for account_name, stats in sorted(accounts.items()):
        print(f"  {account_name}:")
        print(f"    记录数: {stats['count']}")
        print(f"    总消耗: {stats['cost']:.2f} 元")
        print(f"    总转化: {stats['convert']}")
        if stats['convert'] > 0:
            print(f"    平均成本: {stats['cost'] / stats['convert']:.2f} 元/转化")
        print()

if __name__ == '__main__':
    main()
