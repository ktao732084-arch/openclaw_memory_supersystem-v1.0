#!/usr/bin/env python3
"""
测试v2客资接口的不同token传递方式
"""
import requests
import json
from datetime import datetime, timedelta
from token_manager import get_valid_token

ADVERTISER_ID = 1769665409798152

def test_v2_methods():
    """测试v2接口的不同调用方式"""
    
    access_token = get_valid_token()
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    start_time = f"{yesterday} 00:00:00"
    end_time = f"{yesterday} 23:59:59"
    
    url = "https://api.oceanengine.com/open_api/2/tools/clue/get/"
    
    print(f"📊 测试v2客资接口的不同调用方式")
    print(f"   URL: {url}")
    print(f"   日期: {yesterday}")
    print()
    
    # 方法1：Query参数传token
    print("🔍 方法1: Query参数传token")
    try:
        params = {
            "advertiser_id": ADVERTISER_ID,
            "start_time": start_time,
            "end_time": end_time,
            "page": 1,
            "page_size": 10,
            "access_token": access_token
        }
        resp = requests.get(url, params=params, timeout=10)
        print(f"   状态码: {resp.status_code}")
        result = resp.json()
        print(f"   响应: {json.dumps(result, ensure_ascii=False, indent=6)}")
    except Exception as e:
        print(f"   ❌ 异常: {e}")
    print()
    
    # 方法2：Header传token（Access-Token）
    print("🔍 方法2: Header传token（Access-Token）")
    try:
        params = {
            "advertiser_id": ADVERTISER_ID,
            "start_time": start_time,
            "end_time": end_time,
            "page": 1,
            "page_size": 10
        }
        headers = {"Access-Token": access_token}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"   状态码: {resp.status_code}")
        result = resp.json()
        print(f"   响应: {json.dumps(result, ensure_ascii=False, indent=6)}")
    except Exception as e:
        print(f"   ❌ 异常: {e}")
    print()
    
    # 方法3：Header传token（Authorization）
    print("🔍 方法3: Header传token（Authorization Bearer）")
    try:
        params = {
            "advertiser_id": ADVERTISER_ID,
            "start_time": start_time,
            "end_time": end_time,
            "page": 1,
            "page_size": 10
        }
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"   状态码: {resp.status_code}")
        result = resp.json()
        print(f"   响应: {json.dumps(result, ensure_ascii=False, indent=6)}")
    except Exception as e:
        print(f"   ❌ 异常: {e}")
    print()
    
    # 方法4：POST请求
    print("🔍 方法4: POST请求 + JSON body")
    try:
        payload = {
            "advertiser_id": ADVERTISER_ID,
            "start_time": start_time,
            "end_time": end_time,
            "page": 1,
            "page_size": 10
        }
        headers = {
            "Access-Token": access_token,
            "Content-Type": "application/json"
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"   状态码: {resp.status_code}")
        result = resp.json()
        print(f"   响应: {json.dumps(result, ensure_ascii=False, indent=6)}")
    except Exception as e:
        print(f"   ❌ 异常: {e}")

if __name__ == '__main__':
    test_v2_methods()
