#!/usr/bin/env python3
"""
获取多维表格下所有数据表列表
"""
import requests

FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = "REDACTED"
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"

def get_tables():
    """获取所有数据表"""
    print("🔑 获取访问令牌...")
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    
    resp = requests.post(url, json=payload, timeout=10)
    data = resp.json()
    
    if data.get('code') != 0:
        print(f"❌ 获取令牌失败: {data}")
        return
    
    token = data['tenant_access_token']
    print(f"✓ 令牌获取成功\n")
    
    # 获取表格列表
    print("📊 获取数据表列表...")
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    resp = requests.get(url, headers=headers, timeout=10)
    data = resp.json()
    
    if data.get('code') == 0:
        tables = data.get('data', {}).get('items', [])
        print(f"✓ 找到 {len(tables)} 个数据表：\n")
        
        for i, table in enumerate(tables, 1):
            print(f"{i}. 表名: {table.get('name')}")
            print(f"   Table ID: {table.get('table_id')}")
            print(f"   记录数: {table.get('record_count', 'N/A')}")
            print()
    else:
        print(f"❌ 获取失败: {data.get('msg')}")
        print(f"   错误码: {data.get('code')}")

if __name__ == '__main__':
    get_tables()
