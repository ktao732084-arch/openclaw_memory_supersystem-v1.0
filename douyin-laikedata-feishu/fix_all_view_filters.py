#!/usr/bin/env python3
"""
为所有账户视图添加筛选条件
包括已存在的视图和新创建的视图
"""

import requests
import time

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

def list_views():
    """列出所有视图"""
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/views"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers, timeout=10)
    return response.json()['data']['items']

def get_all_accounts():
    """获取所有账户名称"""
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
    
    return accounts

def update_view_filter(view_id, view_name, account_name, text_field_id, date_field_id):
    """更新视图筛选条件"""
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/views/{view_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 构建完整的视图配置
    data = {
        "view_name": view_name,
        "property": {
            "filter_info": {
                "conjunction": "and",
                "conditions": [
                    {
                        "field_id": text_field_id,
                        "operator": "is",
                        "value": account_name  # 直接传字符串，不是数组
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
    
    response = requests.patch(url, headers=headers, json=data, timeout=10)
    result = response.json()
    
    if result.get('code') == 0:
        print(f"✅ 已更新视图: {view_name}")
        print(f"   筛选: 文本 = {account_name}")
        print(f"   排序: 按日期降序")
        return True
    else:
        print(f"❌ 更新失败: {view_name}")
        print(f"   错误: {result}")
        return False

def main():
    print("=" * 80)
    print("为所有账户视图添加筛选条件")
    print("=" * 80)
    
    print("\n步骤1: 获取字段ID...")
    text_field_id = get_field_id_by_name("文本")
    date_field_id = get_field_id_by_name("时间")
    
    if not text_field_id or not date_field_id:
        print("❌ 无法获取字段ID")
        return
    
    print(f"  文本字段ID: {text_field_id}")
    print(f"  时间字段ID: {date_field_id}")
    
    print("\n步骤2: 获取所有账户...")
    accounts = get_all_accounts()
    print(f"找到 {len(accounts)} 个账户")
    
    print("\n步骤3: 获取所有视图...")
    views = list_views()
    print(f"找到 {len(views)} 个视图")
    
    print("\n步骤4: 匹配并更新视图...")
    success_count = 0
    skipped_count = 0
    
    for view in views:
        view_name = view['view_name']
        view_id = view['view_id']
        
        # 跳过默认视图
        if view_name == "表格":
            print(f"  ⏭️  跳过默认视图: {view_name}")
            skipped_count += 1
            continue
        
        # 查找匹配的账户
        matched_account = None
        for account in accounts:
            if account in view_name or view_name in account:
                matched_account = account
                break
        
        if matched_account:
            print(f"\n  处理视图: {view_name}")
            print(f"  匹配账户: {matched_account}")
            if update_view_filter(view_id, view_name, matched_account, text_field_id, date_field_id):
                success_count += 1
            time.sleep(0.5)  # 避免API限流
        else:
            print(f"  ⚠️  未匹配到账户: {view_name}")
            skipped_count += 1
    
    print("\n" + "=" * 80)
    print(f"✅ 完成！")
    print(f"   成功更新: {success_count} 个视图")
    print(f"   跳过: {skipped_count} 个视图")
    print("=" * 80)
    
    print("\n请访问飞书多维表格验证:")
    print("https://ocnbk46uzxq8.feishu.cn/base/FEiCbGEDHarzyUsPG8QcoLxwn7d")
    print("\n检查要点:")
    print("1. 每个账户视图只显示对应账户的数据")
    print("2. 数据按日期降序排列")
    print("3. 新数据自动归类到对应视图")

if __name__ == "__main__":
    main()
