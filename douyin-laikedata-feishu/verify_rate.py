#!/usr/bin/env python3
import requests

FEISHU_APP_ID = 'cli_a90737e0f5b81cd3'
FEISHU_APP_SECRET = 'REDACTED'
FEISHU_APP_TOKEN = 'FEiCbGEDHarzyUsPG8QcoLxwn7d'
TABLE_TOUFA = 'tbl1n1PC1aooYdKk'

url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
resp = requests.post(url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET})
token = resp.json()['tenant_access_token']

url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_TOUFA}/records'
headers = {'Authorization': f'Bearer {token}'}

resp = requests.get(url, headers=headers, params={'page_size': 500})
data = resp.json()

items = data.get('data', {}).get('items', [])

print('客资转化率验证:\n')
count = 0
for item in items:
    f = item.get('fields', {})
    k = f.get('客资数量', '0')
    c = f.get('转化数', '0')
    r = f.get('客资转化率(%)', '0')
    n = f.get('单元名称', '?')
    
    if k and k != '0':
        count += 1
        print(f'{count}. {n}: 客资{k}, 转化{c}, 转化率{r}%')
        if count >= 10:
            break
