#!/usr/bin/env python3
"""
修复账户视图筛选条件
确保每个视图只显示对应账户的数据
"""

import requests

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

# 7个有数据的账户
ACTIVE_ACCOUNTS = {
    1835880409219083: "郑州天后医疗美容医院有限公司-XL",
    1844477765429641: "DX-郑州天后医疗美容医院",
    1844577767982090: "本地推-ka-郑州天后医疗美容医院有限公司",
    1847370973597827: "菲象_郑州天后_10",
    1848003626326092: "菲象_郑州天后_27",
    1848660180442243: "菲象_郑州天后_新",
    1856270852478087: "郑州天后医疗美容-智慧本地推-1",
}

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    response = requests.post(url, headers=headers, json=data, timeout=5)
    return response.json()['tenant_access_token']

def list_views():
    """列出所有视图"""
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/views"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers, timeout=10)
    return response.json()['data']['items']

def get_view_detail(view_id):
    """获取视图详情"""
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/views/{view_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers, timeout=10)
    return response.json()['data']

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

def update_view_filter(view_id, view_name, account_name):
    """更新视图筛选条件"""
    token = get_token()
    
    # 获取"文本"字段的ID
    text_field_id = get_field_id_by_name("文本")
    if not text_field_id:
        print(f"❌ 找不到'文本'字段")
        return False
    
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/views/{view_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 构建筛选条件
    data = {
        "view_name": view_name,
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
    
    response = requests.patch(url, headers=headers, json=data, timeout=10)
    result = response.json()
    
    if result.get('code') == 0:
        print(f"✅ 已更新视图: {view_name}")
        print(f"   筛选条件: 文本 = {account_name}")
        return True
    else:
        print(f"❌ 更新失败: {view_name}")
        print(f"   错误: {result}")
        return False

def main():
    print("=" * 80)
    print("修复账户视图筛选条件")
    print("=" * 80)
    
    print("\n步骤1: 获取所有视图...")
    views = list_views()
    print(f"找到 {len(views)} 个视图")
    
    print("\n步骤2: 匹配账户视图...")
    account_views = {}
    for view in views:
        view_name = view['view_name']
        # 检查视图名称是否匹配账户名称
        for account_name in ACTIVE_ACCOUNTS.values():
            if account_name in view_name or view_name in account_name:
                account_views[view['view_id']] = {
                    'name': view_name,
                    'account': account_name
                }
                print(f"  匹配: {view_name} → {account_name}")
                break
    
    print(f"\n找到 {len(account_views)} 个账户视图")
    
    print("\n步骤3: 更新筛选条件...")
    success_count = 0
    for view_id, info in account_views.items():
        if update_view_filter(view_id, info['name'], info['account']):
            success_count += 1
    
    print("\n" + "=" * 80)
    print(f"✅ 完成！成功更新 {success_count}/{len(account_views)} 个视图")
    print("=" * 80)
    
    print("\n请访问飞书多维表格验证:")
    print("https://ocnbk46uzxq8.feishu.cn/base/FEiCbGEDHarzyUsPG8QcoLxwn7d")
    print("\n检查要点:")
    print("1. 每个账户视图只显示对应账户的数据")
    print("2. 数据按日期降序排列")

if __name__ == "__main__":
    main()
