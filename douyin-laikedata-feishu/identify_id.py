#!/usr/bin/env python3
"""
尝试识别ID类型
"""
import requests
import json

ACCESS_TOKEN = "REDACTED"
ADVERTISER_ID = 1769665409798152
TEST_ID = 272328498099752

print("="*60)
print(f"尝试识别ID: {TEST_ID}")
print("="*60 + "\n")

# 1. 尝试作为广告主ID
print("1️⃣ 尝试作为广告主ID...")
url = "https://api.oceanengine.com/open_api/2/advertiser/info/"
headers = {"Access-Token": ACCESS_TOKEN}
params = {"advertiser_ids": json.dumps([TEST_ID])}

try:
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    data = resp.json()
    print(f"   响应: {json.dumps(data, indent=2, ensure_ascii=False)}\n")
except Exception as e:
    print(f"   异常: {e}\n")

# 2. 尝试获取当前授权的所有账户
print("2️⃣ 获取当前授权的广告主列表...")
url = "https://api.oceanengine.com/open_api/oauth2/advertiser/get/"
headers = {"Access-Token": ACCESS_TOKEN}
params = {"page": 1, "page_size": 100}

try:
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    data = resp.json()
    
    if data.get('code') == 0:
        advertisers = data.get('data', {}).get('list', [])
        print(f"   ✅ 找到 {len(advertisers)} 个授权的广告主:\n")
        
        for adv in advertisers:
            adv_id = adv.get('advertiser_id')
            adv_name = adv.get('advertiser_name', '未知')
            print(f"   - {adv_id}: {adv_name}")
            
            # 检查是否匹配
            if str(adv_id) == str(TEST_ID):
                print(f"     ✅ 匹配！这是一个广告主ID")
    else:
        print(f"   ❌ 失败: {data.get('message')}")
        print(f"   完整响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
except Exception as e:
    print(f"   异常: {e}")

print("\n" + "="*60)
print("💡 提示:")
print("   如果这个ID是从巨量后台复制的，请确认：")
print("   1. 是否是'本地推账户ID'（不是广告主ID）")
print("   2. 路径：本地推 → 账户设置 → 账户信息")
print("   3. 或者提供截图，我帮你找正确的ID")
print("="*60)
