#!/usr/bin/env python3
"""
Gateway集群控制器 - 电脑端控制测试
"""

import requests
import json
import time

# 电脑端Gateway配置
GATEWAY_URL = "http://localhost:18789"
AUTH_TOKEN = "1784d642c317579659a71f62a6660c57"

def test_gateway_connection():
    """测试Gateway连接"""
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print("🔧 测试Gateway连接...")
    
    # 测试不同的API端点
    endpoints = [
        "/api/health",
        "/api/sessions",
        "/api/agents", 
        "/api/gateway/status"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"📍 测试端点: {endpoint}")
            response = requests.get(f"{GATEWAY_URL}{endpoint}", headers=headers, timeout=5)
            
            if response.status_code == 200:
                print(f"✅ {endpoint} - 状态码: {response.status_code}")
                # 尝试解析JSON响应
                try:
                    json_data = response.json()
                    print(f"📄 响应数据: {json.dumps(json_data, indent=2, ensure_ascii=False)}")
                except:
                    print(f"📄 响应内容: {response.text[:200]}...")
            else:
                print(f"❌ {endpoint} - 状态码: {response.status_code}")
                print(f"📄 响应内容: {response.text[:200]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint} - 连接错误: {e}")
        
        print("-" * 50)
        time.sleep(1)

def create_test_session():
    """创建测试会话"""
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "label": "test-controller",
        "message": "这是一条来自主Gateway的测试消息"
    }
    
    print("🧪 创建测试会话...")
    try:
        response = requests.post(
            f"{GATEWAY_URL}/api/sessions", 
            headers=headers, 
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ 测试会话创建成功")
            return response.json()
        else:
            print(f"❌ 测试会话创建失败 - 状态码: {response.status_code}")
            print(f"📄 响应内容: {response.text[:200]}...")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 测试会话创建失败 - 连接错误: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Gateway集群控制测试开始")
    print("=" * 60)
    
    # 测试连接
    test_gateway_connection()
    
    # 创建测试会话
    print("\n🚀 创建测试会话...")
    result = create_test_session()
    
    print("\n📋 测试完成")
    print("如果连接测试成功，我们可以继续实施Gateway集群控制方案")