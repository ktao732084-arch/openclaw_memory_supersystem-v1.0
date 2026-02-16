#!/usr/bin/env python3
"""
测试公式字段是否正常工作
"""
import requests
import json

# 飞书配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "REDACTED"
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def get_feishu_token():
    """获取飞书访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    resp = requests.post(url, json=payload, timeout=10)
    return resp.json()['tenant_access_token']

def test_formula_fields():
    """测试公式字段"""
    print("="*60)
    print("测试公式字段")
    print("="*60)
    print()
    
    token = get_feishu_token()
    
    # 获取最新的几条记录
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page_size": 5}
    
    resp = requests.get(url, headers=headers, params=params)
    data = resp.json()
    
    if data.get('code') == 0:
        records = data['data']['items']
        print(f"获取到 {len(records)} 条记录\n")
        
        for i, record in enumerate(records, 1):
            fields = record['fields']
            print(f"记录 {i}:")
            print(f"  账户名称: {fields.get('文本', 'N/A')}")
            print(f"  日期: {fields.get('时间', 'N/A')}")
            print(f"  单元名称: {fields.get('单元名称', 'N/A')}")
            print(f"  消耗(元): {fields.get('消耗(元)', 'N/A')}")
            print(f"  转化数: {fields.get('转化数', 'N/A')}")
            
            # 检查公式字段
            kezi_count = fields.get('客资数量', 'N/A')
            actual_cost = fields.get('实际获客成本', 'N/A')
            conversion_rate = fields.get('客资转化率(%)', 'N/A')
            
            print(f"  ✅ 客资数量: {kezi_count}")
            print(f"  ✅ 实际获客成本: {actual_cost}")
            print(f"  ✅ 客资转化率(%): {conversion_rate}")
            print()
        
        # 检查是否有公式字段
        has_kezi_count = any('客资数量' in r['fields'] for r in records)
        has_actual_cost = any('实际获客成本' in r['fields'] for r in records)
        has_conversion_rate = any('客资转化率(%)' in r['fields'] for r in records)
        
        print("="*60)
        print("公式字段检查结果:")
        print("="*60)
        print(f"客资数量字段: {'✅ 存在' if has_kezi_count else '❌ 不存在'}")
        print(f"实际获客成本字段: {'✅ 存在' if has_actual_cost else '❌ 不存在'}")
        print(f"客资转化率(%)字段: {'✅ 存在' if has_conversion_rate else '❌ 不存在'}")
        print()
        
        if has_kezi_count and has_actual_cost and has_conversion_rate:
            print("✅ 所有公式字段配置成功！")
        else:
            print("⚠️  部分公式字段未找到，请检查字段名称")
    else:
        print(f"❌ 获取数据失败: {data}")

if __name__ == '__main__':
    test_formula_fields()
