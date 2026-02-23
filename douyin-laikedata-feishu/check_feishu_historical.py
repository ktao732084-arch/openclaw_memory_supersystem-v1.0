#!/usr/bin/env python3
"""查看飞书表格里的历史数据"""

import requests
import json
from datetime import datetime, timedelta

# 配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def get_feishu_token():
    """获取飞书 Token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    response = requests.post(url, headers=headers, json=data, timeout=10)
    result = response.json()
    if result.get('code') == 0:
        return result['tenant_access_token']
    else:
        raise Exception(f"获取飞书 Token 失败: {result}")

def search_feishu_records(feishu_token, date_str):
    """搜索指定日期的记录"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records/search"
    headers = {"Authorization": f"Bearer {feishu_token}", "Content-Type": "application/json"}
    
    payload = {
        "filter": {
            "conjunction": "and",
            "conditions": [
                {
                    "field_name": "时间",
                    "operator": "is",
                    "value": [date_str]
                }
            ]
        },
        "page_size": 500
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    result = response.json()
    
    if result.get('code') != 0:
        raise Exception(f"查询失败: {result}")
    
    return result.get('data', {}).get('items', [])

def main():
    print("📅 检查飞书表格里的历史数据")
    print("=" * 80)
    
    feishu_token = get_feishu_token()
    
    # 看看过去7天的数据
    for i in range(7, 0, -1):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        print(f"\n🔍 {date}")
        print("-" * 80)
        
        records = search_feishu_records(feishu_token, date)
        
        if records:
            total_cost = 0.0
            total_convert = 0
            
            for r in records:
                fields = r.get('fields', {})
                cost_str = fields.get('消耗(元)', '0')
                try:
                    cost = float(cost_str)
                except:
                    cost = 0.0
                total_cost += cost
                
                convert_str = fields.get('转化数', '0')
                try:
                    convert = int(convert_str)
                except:
                    convert = 0
                total_convert += convert
            
            print(f"  记录数: {len(records)}")
            print(f"  总消耗: {total_cost}")
            print(f"  总转化: {total_convert}")
            
            if total_cost > 0:
                print(f"  ✅ 有消耗数据！")
                # 显示前几条有消耗的
                for r in records[:3]:
                    fields = r.get('fields', {})
                    cost = fields.get('消耗(元)', '0')
                    if float(cost) > 0:
                        print(f"    - {fields.get('单元名称', '')}: {cost}")
        else:
            print("  ⚠️  无数据")

if __name__ == "__main__":
    main()
