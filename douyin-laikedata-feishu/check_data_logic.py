#!/usr/bin/env python3
"""检查数据逻辑"""

import requests

FEISHU_APP_ID = 'cli_a90737e0f5b81cd3'
FEISHU_APP_SECRET = 'REDACTED'
FEISHU_APP_TOKEN = 'FEiCbGEDHarzyUsPG8QcoLxwn7d'
TABLE_TOUFA = 'tbl1n1PC1aooYdKk'

def get_token():
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    resp = requests.post(url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET})
    return resp.json()['tenant_access_token']

token = get_token()

# 获取最近20条数据
url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_TOUFA}/records'
resp = requests.get(url, headers={'Authorization': f'Bearer {token}'}, params={'page_size': 20})
records = resp.json()['data']['items']

print('\n📊 最近20条数据检查:\n')
print(f'{"日期":<12} {"单元名称":<28} {"转化":<6} {"客资":<6} {"关系":<10}')
print('-' * 75)

abnormal_count = 0
for r in records:
    f = r['fields']
    date = f.get('时间', '')
    name = f.get('单元名称', '')[:26]
    
    try:
        convert = int(f.get('转化数', '0'))
        kezi = int(f.get('客资数量', '0'))
        
        if kezi > convert:
            relation = f'⚠️ 客资>{convert}'
            abnormal_count += 1
        elif kezi == convert:
            relation = '✓ 相等'
        else:
            relation = f'✓ 转化>{kezi}'
        
        print(f'{date:<12} {name:<28} {convert:<6} {kezi:<6} {relation:<10}')
    except Exception as e:
        print(f'{date:<12} {name:<28} 数据错误: {e}')

print(f'\n\n📈 统计结果:')
print(f'   总记录数: {len(records)}')
print(f'   异常记录: {abnormal_count} 条（客资数 > 转化数）')

if abnormal_count > 0:
    print(f'\n⚠️  发现 {abnormal_count} 条异常数据！')
    print('   这不符合正常逻辑（转化数应该 >= 客资数）')
    print('   可能原因：')
    print('   1. 客资统计的是累计数据，而不是按日期统计')
    print('   2. 客资数据和投放数据的日期不匹配')
    print('   3. 单元ID匹配有问题')
else:
    print('\n✅ 所有数据正常（转化数 >= 客资数）')
