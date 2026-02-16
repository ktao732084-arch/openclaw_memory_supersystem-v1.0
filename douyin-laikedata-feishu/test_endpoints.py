#!/usr/bin/env python3
"""
测试巨量引擎多个 API 端点
"""
import requests
import json
from datetime import datetime, timedelta

ACCESS_TOKEN = "REDACTED"
ADVERTISER_ID = 1769665409798152

def test_api(name, url, method="GET", payload=None):
    """测试单个 API"""
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"URL: {url}")
    print('='*60)
    
    headers = {
        "Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, params=payload, timeout=10)
        else:
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
        
        print(f"状态码: {resp.status_code}")
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
                
                if data.get('code') == 0:
                    print("✅ 成功")
                    return data
                else:
                    print(f"❌ 错误: {data.get('message')}")
            except:
                print(f"原始响应: {resp.text[:200]}")
        else:
            print(f"❌ HTTP错误: {resp.text[:200]}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    return None

# 测试多个端点
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

# 1. 广告计划列表
test_api(
    "广告计划列表",
    "https://api.oceanengine.com/open_api/2/campaign/get/",
    "GET",
    {"advertiser_id": ADVERTISER_ID, "page": 1, "page_size": 10}
)

# 2. 广告组列表
test_api(
    "广告组列表",
    "https://api.oceanengine.com/open_api/2/ad/get/",
    "GET",
    {"advertiser_id": ADVERTISER_ID, "page": 1, "page_size": 10}
)

# 3. 报表API v1.0
test_api(
    "报表API v1.0",
    "https://api.oceanengine.com/open_api/v1.0/report/ad/get/",
    "GET",
    {
        "advertiser_id": ADVERTISER_ID,
        "start_date": yesterday,
        "end_date": yesterday,
        "page": 1,
        "page_size": 10
    }
)

# 4. 报表API v3.0
test_api(
    "报表API v3.0",
    "https://api.oceanengine.com/open_api/v3.0/report/ad/get/",
    "GET",
    {
        "advertiser_id": ADVERTISER_ID,
        "start_date": yesterday,
        "end_date": yesterday,
        "page": 1,
        "page_size": 10
    }
)

print("\n" + "="*60)
print("测试完成")
print("="*60)
