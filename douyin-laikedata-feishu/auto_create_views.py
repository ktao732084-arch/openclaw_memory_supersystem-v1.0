#!/usr/bin/env python3
"""
自动检测新账户并创建对应视图
可以加入到定时任务中，每天自动运行
"""

import requests

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "REDACTED"
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    response = requests.post(url, headers=headers, json=data, timeout=5)
    return response.json()['tenant_access_token']

def get_all_accounts():
    """获取数据表中所有不同的账户名称"""
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
    headers = {"Authorization": f"Bearer {token}"}
    
    accounts = set()
    page_token = None
    
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        result = response.json()
        
        for record in result['data']['items']:
            account = record['fields'].get('文本', '')
            if account:
                accounts.add(account)
        
        if not result['data'].get('has_more'):
            break
        page_token = result['data'].get('page_token')
    
    return sorted(accounts)

def get_existing_views():
    """获取现有的所有视图名称"""
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/views"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers, timeout=10)
    
    views = {}
    for view in response.json()['data']['items']:
        views[view['view_name']] = view['view_id']
    
    return views

def get_field_id_by_name(field_name):
    """根据字段名获取字段ID"""
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/fields"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers, timeout=10)
    fields = response.json()['data']['items']
    
    for field in fields:
        if field['field_name'] == field_name:
            return field['field_id']
    return None

def create_account_view(account_name, text_field_id, date_field_id):
    """创建账户视图并配置筛选条件"""
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/views"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "view_name": account_name,
        "view_type": "grid",  # 表格视图
        "filter_info": {
            "conjunction": "and",
            "conditions": [
                {
                    "field_id": text_field_id,
                    "operator": "is",
                    "value": [account_name]
                }
            ]
        },
        "property": {
            "filter_info": {
                "conjunction": "and",
                "conditions": [
                    {
                        "field_id": text_field_id,
                        "operator": "is",
                        "value": [account_name]
                    }
                ]
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=10)
    result = response.json()
    
    if result.get('code') == 0:
        view_id = result['data']['view']['view_id']
        print(f"✅ 已创建视图: {account_name}")
        
        # 设置排序（按日期降序）
        set_view_sort(view_id, date_field_id)
        return True
    else:
        print(f"❌ 创建失败: {account_name}")
        print(f"   错误: {result}")
        return False

def set_view_sort(view_id, date_field_id):
    """设置视图排序（按日期降序）"""
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/views/{view_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "property": {
            "sort_info": [
                {
                    "field_id": date_field_id,
                    "desc": True  # 降序
                }
            ]
        }
    }
    
    response = requests.patch(url, headers=headers, json=data, timeout=10)
    if response.json().get('code') == 0:
        print(f"   ✅ 已设置排序: 按日期降序")

def main():
    print("=" * 80)
    print("自动检测新账户并创建视图")
    print("=" * 80)
    
    print("\n步骤1: 获取所有账户...")
    accounts = get_all_accounts()
    print(f"找到 {len(accounts)} 个不同的账户")
    
    print("\n步骤2: 获取现有视图...")
    existing_views = get_existing_views()
    print(f"现有 {len(existing_views)} 个视图")
    
    print("\n步骤3: 检测新账户...")
    new_accounts = []
    for account in accounts:
        if account not in existing_views:
            new_accounts.append(account)
            print(f"  🆕 新账户: {account}")
    
    if not new_accounts:
        print("  ✅ 没有新账户，无需创建视图")
        return
    
    print(f"\n找到 {len(new_accounts)} 个新账户")
    
    print("\n步骤4: 获取字段ID...")
    text_field_id = get_field_id_by_name("文本")
    date_field_id = get_field_id_by_name("时间")
    
    if not text_field_id or not date_field_id:
        print("❌ 无法获取字段ID")
        return
    
    print(f"  文本字段ID: {text_field_id}")
    print(f"  时间字段ID: {date_field_id}")
    
    print("\n步骤5: 创建新视图...")
    success_count = 0
    for account in new_accounts:
        if create_account_view(account, text_field_id, date_field_id):
            success_count += 1
    
    print("\n" + "=" * 80)
    print(f"✅ 完成！成功创建 {success_count}/{len(new_accounts)} 个视图")
    print("=" * 80)
    
    print("\n视图配置:")
    print("  - 筛选条件: 文本 = 对应账户名称")
    print("  - 排序规则: 按日期降序")
    print("  - 自动归类: 新数据自动显示")

if __name__ == "__main__":
    main()
