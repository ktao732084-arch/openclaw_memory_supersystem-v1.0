#!/usr/bin/env python3
"""在数据表中创建客资统计字段"""

import requests

FEISHU_APP_ID = 'cli_a90737e0f5b81cd3'
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = 'FEiCbGEDHarzyUsPG8QcoLxwn7d'
TABLE_TOUFA = 'tbl1n1PC1aooYdKk'

def get_token():
    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    resp = requests.post(url, json={'app_id': FEISHU_APP_ID, 'app_secret': FEISHU_APP_SECRET})
    return resp.json()['tenant_access_token']

def create_field(token, field_name, field_type=1):
    """创建字段
    field_type: 1=文本, 2=数字, 15=URL
    """
    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{TABLE_TOUFA}/fields'
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    payload = {
        'field_name': field_name,
        'type': field_type
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    data = resp.json()
    
    if data.get('code') == 0:
        print(f"✓ 创建字段: {field_name}")
        return data.get('data', {}).get('field', {}).get('field_id')
    else:
        print(f"❌ 创建字段失败 {field_name}: {data.get('msg')}")
        return None

def main():
    print("📝 创建客资统计字段...\n")
    
    token = get_token()
    
    # 创建4个新字段
    fields_to_create = [
        ('客资数量', 1),           # 文本类型
        ('实际获客成本', 1),        # 文本类型
        ('客资转化率(%)', 1),      # 文本类型
        ('客资详情', 15)           # URL类型
    ]
    
    for field_name, field_type in fields_to_create:
        create_field(token, field_name, field_type)
    
    print("\n✅ 字段创建完成！")

if __name__ == '__main__':
    main()
