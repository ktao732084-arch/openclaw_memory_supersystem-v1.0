#!/usr/bin/env python3
"""
尝试获取所有本地推账户列表
"""
import requests
import json

ACCESS_TOKEN = "REDACTED"
ADVERTISER_ID = 1769665409798152

print("="*60)
print("尝试获取所有本地推账户")
print("="*60 + "\n")

# 尝试多个可能的API端点
endpoints = [
    {
        "name": "本地推账户列表 v3.0",
        "url": "https://api.oceanengine.com/open_api/v3.0/local/account/list/",
        "params": {"advertiser_id": ADVERTISER_ID, "page": 1, "page_size": 100}
    },
    {
        "name": "本地推账户列表 v2",
        "url": "https://api.oceanengine.com/open_api/2/local/account/list/",
        "params": {"advertiser_id": ADVERTISER_ID, "page": 1, "page_size": 100}
    },
    {
        "name": "本地推账户获取",
        "url": "https://api.oceanengine.com/open_api/v3.0/local_account/list/",
        "params": {"advertiser_id": ADVERTISER_ID, "page": 1, "page_size": 100}
    },
    {
        "name": "本地推项目列表（获取账户信息）",
        "url": "https://api.oceanengine.com/open_api/v3.0/local/project/list/",
        "params": {"advertiser_id": ADVERTISER_ID, "page": 1, "page_size": 100}
    }
]

headers = {
    "Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

for endpoint in endpoints:
    print(f"🔍 尝试: {endpoint['name']}")
    print(f"   URL: {endpoint['url']}")
    
    try:
        resp = requests.get(endpoint['url'], headers=headers, params=endpoint['params'], timeout=10)
        data = resp.json()
        
        print(f"   状态码: {resp.status_code}")
        print(f"   响应码: {data.get('code')}")
        print(f"   消息: {data.get('message')}")
        
        if data.get('code') == 0:
            print(f"   ✅ 成功！")
            print(f"   响应数据: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}...")
            
            # 尝试提取账户列表
            data_obj = data.get('data', {})
            
            # 尝试不同的字段名
            for key in ['list', 'account_list', 'local_account_list', 'project_list']:
                if key in data_obj:
                    items = data_obj[key]
                    print(f"\n   📋 找到字段: {key}, 共 {len(items)} 条")
                    
                    if items and len(items) > 0:
                        print(f"   第一条数据: {json.dumps(items[0], indent=2, ensure_ascii=False)}")
                    break
            
            break
        else:
            print(f"   ❌ 失败")
        
        print()
        
    except Exception as e:
        print(f"   ❌ 异常: {e}\n")

print("="*60)
print("💡 如果以上都失败，可能需要：")
print("1. 查看巨量引擎API文档，找到正确的账户列表接口")
print("2. 或者手动提供所有账户ID列表")
print("3. 或者通过项目列表反推账户ID")
print("="*60)
