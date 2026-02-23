#!/usr/bin/env python3
"""
获取本地推账户列表
"""
import requests
import json

ACCESS_TOKEN = os.getenv('JULIANG_ACCESS_TOKEN')
ADVERTISER_ID = 1769665409798152

def get_local_accounts():
    """获取本地推账户列表"""
    print("🔍 获取本地推账户列表...\n")
    
    # 尝试几个可能的端点
    endpoints = [
        "https://api.oceanengine.com/open_api/v3.0/local/account/get/",
        "https://api.oceanengine.com/open_api/2/local/account/get/",
        "https://api.oceanengine.com/open_api/v3.0/local_account/get/",
    ]
    
    headers = {
        "Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    params = {
        "advertiser_id": ADVERTISER_ID
    }
    
    for url in endpoints:
        print(f"尝试: {url}")
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"状态码: {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}\n")
                
                if data.get('code') == 0:
                    print("✅ 找到了！")
                    return data
            else:
                print(f"响应: {resp.text[:200]}\n")
        except Exception as e:
            print(f"错误: {e}\n")
    
    print("❌ 未找到可用的本地推账户列表接口")
    return None

if __name__ == '__main__':
    result = get_local_accounts()
    
    if not result:
        print("\n" + "="*60)
        print("建议：")
        print("1. 在巨量引擎后台查看本地推账户ID")
        print("2. 路径：本地推 → 账户设置 → 账户信息")
        print("3. 或者提供本地推的 API 文档链接")
        print("="*60)
