#!/usr/bin/env python3
"""
批量创建账户视图
"""
import requests
import time

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

# 7个有数据的账户
ACCOUNTS = [
    "郑州天后医疗美容医院有限公司-XL",
    "DX-郑州天后医疗美容医院",
    "本地推-ka-郑州天后医疗美容医院有限公司",
    "菲象_郑州天后_10",
    "菲象_郑州天后_27",
    "菲象_郑州天后_新",
    "郑州天后医疗美容-智慧本地推-1",
]

def get_feishu_token():
    """获取飞书访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    resp = requests.post(url, json=payload, timeout=10)
    return resp.json()['tenant_access_token']

def get_field_id(token, field_name):
    """获取字段ID"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/fields"
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(url, headers=headers, timeout=10)
    result = resp.json()
    
    if result.get('code') == 0:
        for field in result['data']['items']:
            if field['field_name'] == field_name:
                return field['field_id']
    return None

def create_view(token, account_name, account_field_id, date_field_id):
    """为账户创建视图"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/views"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    payload = {
        "view_name": account_name,
        "view_type": "grid",
        "property": {
            "filter_info": {
                "conjunction": "and",
                "conditions": [
                    {
                        "field_id": account_field_id,
                        "operator": "is",
                        "value": [account_name]
                    }
                ]
            },
            "sort_info": [
                {
                    "field_id": date_field_id,
                    "desc": True
                }
            ]
        }
    }
    
    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    result = resp.json()
    
    return result

def main():
    print("="*60)
    print("批量创建账户视图")
    print("="*60)
    print()
    
    # 获取 token
    print("1. 获取飞书访问令牌...")
    token = get_feishu_token()
    print("   ✓ Token 获取成功")
    print()
    
    # 获取字段ID
    print("2. 获取字段ID...")
    account_field_id = get_field_id(token, "文本")  # 账户名称字段
    date_field_id = get_field_id(token, "时间")  # 日期字段
    
    if not account_field_id or not date_field_id:
        print("   ❌ 字段ID获取失败")
        print(f"   账户字段ID: {account_field_id}")
        print(f"   日期字段ID: {date_field_id}")
        return
    
    print(f"   ✓ 账户字段ID: {account_field_id}")
    print(f"   ✓ 日期字段ID: {date_field_id}")
    print()
    
    # 批量创建视图
    print("3. 批量创建视图...")
    success_count = 0
    
    for i, account in enumerate(ACCOUNTS, 1):
        print(f"   [{i}/{len(ACCOUNTS)}] {account}...", end=" ", flush=True)
        
        result = create_view(token, account, account_field_id, date_field_id)
        
        if result.get('code') == 0:
            print("✓")
            success_count += 1
        else:
            error_msg = result.get('msg', '未知错误')
            print(f"✗ ({error_msg})")
        
        # 避免API限流
        time.sleep(0.5)
    
    print()
    print("="*60)
    print(f"完成！成功创建 {success_count}/{len(ACCOUNTS)} 个视图")
    print("="*60)

if __name__ == '__main__':
    main()
