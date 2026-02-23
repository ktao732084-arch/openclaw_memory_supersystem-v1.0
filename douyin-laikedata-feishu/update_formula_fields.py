#!/usr/bin/env python3
"""
更新飞书多维表格公式字段
改为引用Sheet2（原始客资数据）
"""

import requests

# 飞书配置（硬编码）
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def get_tenant_access_token():
    """获取飞书 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    
    print("正在获取飞书 token...")
    response = requests.post(url, headers=headers, json=data, timeout=10)
    result = response.json()
    
    if result.get('code') == 0:
        print("✅ Token 获取成功")
        return result['tenant_access_token']
    else:
        raise Exception(f"获取 token 失败: {result}")

def list_fields():
    """列出所有字段"""
    token = get_tenant_access_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/fields"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("正在获取字段列表...")
    response = requests.get(url, headers=headers, timeout=10)
    result = response.json()
    
    if result.get('code') == 0:
        print(f"✅ 获取到 {len(result['data']['items'])} 个字段")
        return result['data']['items']
    else:
        raise Exception(f"获取字段列表失败: {result}")

def delete_field(field_id, field_name):
    """删除字段"""
    token = get_tenant_access_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/fields/{field_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"正在删除字段: {field_name}...")
    response = requests.delete(url, headers=headers, timeout=10)
    result = response.json()
    
    if result.get('code') == 0:
        print(f"✅ 已删除字段: {field_name}")
        return True
    else:
        print(f"❌ 删除字段失败: {field_name}, {result}")
        return False

def create_formula_field(field_name, formula):
    """创建公式字段"""
    token = get_tenant_access_token()
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/fields"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "field_name": field_name,
        "type": 20,  # 公式类型
        "property": {
            "formula": formula
        }
    }
    
    print(f"正在创建字段: {field_name}...")
    response = requests.post(url, headers=headers, json=data, timeout=10)
    result = response.json()
    
    if result.get('code') == 0:
        print(f"✅ 已创建字段: {field_name}")
        return True
    else:
        print(f"❌ 创建字段失败: {field_name}")
        print(f"   错误信息: {result}")
        return False

def main():
    print("=" * 60)
    print("更新飞书多维表格公式字段")
    print("=" * 60)
    
    # 定义新公式（引用Sheet2，使用表ID）
    # Sheet2 表ID: tbl3Oyi6JYt3ZUIP
    formulas = {
        "客资数量": 'FILTER([tbl3Oyi6JYt3ZUIP].[手机号], AND(LEFT([tbl3Oyi6JYt3ZUIP].[单元ID], 15) = LEFT([单元ID], 15), TEXT([tbl3Oyi6JYt3ZUIP].[线索创建时间], "YYYY-MM-DD") = TEXT([时间], "YYYY-MM-DD"))).COUNTA()',
        "实际获客成本": 'IF([客资数量] > 0, [消耗(元)] / [客资数量], 0)',
        "客资转化率(%)": 'IF([客资数量] > 0, ([转化数] / [客资数量]) * 100, 0)'
    }
    
    print("\n步骤1: 获取现有字段列表...")
    fields = list_fields()
    
    # 找到需要删除的字段
    fields_to_delete = {}
    for field in fields:
        field_name = field['field_name']
        if field_name in formulas:
            fields_to_delete[field_name] = field['field_id']
    
    # 删除旧字段
    if fields_to_delete:
        print(f"\n步骤2: 删除旧的公式字段（共{len(fields_to_delete)}个）...")
        for field_name, field_id in fields_to_delete.items():
            delete_field(field_id, field_name)
    else:
        print("\n步骤2: 未找到需要删除的字段，跳过...")
    
    # 创建新字段
    print(f"\n步骤3: 创建新的公式字段（共{len(formulas)}个）...")
    
    # 按顺序创建（客资数量 -> 实际获客成本 -> 客资转化率）
    for field_name in ["客资数量", "实际获客成本", "客资转化率(%)"]:
        formula = formulas[field_name]
        print(f"\n创建字段: {field_name}")
        print(f"公式: {formula[:80]}...")
        create_formula_field(field_name, formula)
    
    print("\n" + "=" * 60)
    print("✅ 公式字段更新完成！")
    print("=" * 60)
    print("\n请访问飞书多维表格查看效果：")
    print("https://ocnbk46uzxq8.feishu.cn/base/FEiCbGEDHarzyUsPG8QcoLxwn7d")
    print("\n检查要点：")
    print("1. 投放数据表中是否有3个新的公式字段")
    print("2. 客资数量字段是否显示数字（不再是0）")
    print("3. 实际获客成本和客资转化率是否正确计算")

if __name__ == "__main__":
    main()
