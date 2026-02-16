#!/usr/bin/env python3
"""
验证抖音来客API的实际可用性
"""
import requests

def test_life_api_endpoints():
    """测试抖音来客可能的API端点"""
    
    print("🔍 测试抖音来客API端点\n")
    
    # 可能的域名和路径
    endpoints = [
        # 教程提到的
        "https://open.douyin.com/goodlife/v1/leads/list",
        "https://open.douyin.com/goodlife/v1/",
        
        # 可能的变体
        "https://open-life.douyin.com/api/v1/leads/list",
        "https://open-life.douyin.com/goodlife/v1/leads/list",
        
        # 巨量引擎的来客接口
        "https://api.oceanengine.com/open_api/v1.0/local_life/clue/list/",
        "https://api.oceanengine.com/open_api/v3.0/local_life/clue/list/",
        
        # 可能的新版本
        "https://open.douyin.com/api/goodlife/v1/leads/list",
    ]
    
    for url in endpoints:
        print(f"测试: {url}")
        try:
            # 不带token，只测试端点是否存在
            resp = requests.get(url, timeout=5)
            print(f"  状态码: {resp.status_code}")
            
            if resp.status_code == 404:
                print(f"  ❌ 端点不存在\n")
            elif resp.status_code in [401, 403]:
                print(f"  ✅ 端点存在（需要认证）\n")
            else:
                print(f"  响应: {resp.text[:200]}\n")
        except requests.exceptions.Timeout:
            print(f"  ⏱️  超时\n")
        except Exception as e:
            print(f"  ❌ 错误: {e}\n")

if __name__ == '__main__':
    test_life_api_endpoints()
