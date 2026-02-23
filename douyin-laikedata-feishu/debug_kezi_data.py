#!/usr/bin/env python3
"""
调试客资数据结构
"""
import requests
import json

FEISHU_APP_ID = 'cli_a90737e0f5b81cd3'
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = 'FEiCbGEDHarzyUsPG8QcoLxwn7d'
TABLE_KEZI = 'tbl3Oyi6JYt3ZUIP'

def get_token():
    """获取飞书访问令牌"""
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    resp = requests.post(url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET})
    return resp.json()['tenant_access_token']

def get_records():
    """获取记录"""
    token = get_token()
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_KEZI}/records'
    headers = {'Authorization': f'Bearer {token}'}
    params = {'page_size': 5}
    
    resp = requests.get(url, headers=headers, params=params)
    data = resp.json()
    
    print("原始响应:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    get_records()
