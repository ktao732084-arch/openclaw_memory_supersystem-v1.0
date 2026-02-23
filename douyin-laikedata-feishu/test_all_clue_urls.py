#!/usr/bin/env python3
"""
全面测试所有可能的线索接口组合
"""
import requests
import json
from datetime import datetime, timedelta

ACCESS_TOKEN = os.getenv('JULIANG_ACCESS_TOKEN')
ADVERTISER_ID = 1769665409798152

yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

# 所有可能的组合
base_urls = [
    "https://api.oceanengine.com",
    "https://ad.oceanengine.com",
]

paths = [
    "/open_api/2/tools/clue/get/",
    "/open_api/v3.0/clue/get/",
    "/open_api/v3.0/local/clue/get/",
    "/open_api/v3.0/tools/clue/get/",
]

headers = {"Access-Token": ACCESS_TOKEN}

params = {
    "advertiser_id": ADVERTISER_ID,
    "start_time": f"{yesterday} 00:00:00",
    "end_time": f"{yesterday} 23:59:59",
    "page": 1,
    "page_size": 10
}

print(f"📊 全面测试线索接口")
print(f"   测试组合数: {len(base_urls) * len(paths)}")
print()

for base in base_urls:
    for path in paths:
        url = base + path
        print(f"测试: {url}")
        
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=5)
            
            if resp.status_code == 404:
                print(f"  ❌ 404\n")
                continue
            
            result = resp.json()
            
            if result.get('code') == 0:
                print(f"  ✅✅✅ 成功！")
                print(json.dumps(result, ensure_ascii=False, indent=2))
                break
            else:
                print(f"  ⚠️  {result.get('code')}: {result.get('message')[:60]}\n")
        
        except Exception as e:
            print(f"  ❌ {str(e)[:60]}\n")
