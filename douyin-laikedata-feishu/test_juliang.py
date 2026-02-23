#!/usr/bin/env python3
"""
测试巨量引擎 API 连接
"""
import requests
import json
import time
import hashlib

JULIANG_APP_ID = "1856818099350592"
JULIANG_SECRET = os.getenv('JULIANG_ACCESS_TOKEN')
JULIANG_ADVERTISER_ID = "1769665409798152"

def get_access_token():
    """获取巨量引擎访问令牌"""
    print("🔑 获取巨量引擎访问令牌...")
    
    url = "https://ad.oceanengine.com/open_api/oauth2/access_token/"
    
    # 巨量引擎使用 app_id + secret 直接获取 token
    params = {
        "app_id": JULIANG_APP_ID,
        "secret": JULIANG_SECRET,
        "grant_type": "auth_code"  # 或 "client_credentials"
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        
        print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if data.get('code') == 0:
            token = data['data']['access_token']
            print(f"✓ 令牌获取成功: {token[:20]}...")
            return token
        else:
            print(f"❌ 获取失败: {data.get('message')}")
            return None
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None

def test_report_api(access_token):
    """测试报表 API"""
    print("\n📊 测试获取报表数据...")
    
    # 巨量引擎报表 API（本地推）
    url = "https://ad.oceanengine.com/open_api/2/report/custom/get/"
    
    headers = {
        "Access-Token": access_token,
        "Content-Type": "application/json"
    }
    
    # 获取昨天的数据
    yesterday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
    
    payload = {
        "advertiser_id": int(JULIANG_ADVERTISER_ID),
        "start_date": yesterday,
        "end_date": yesterday,
        "group_by": ["STAT_GROUP_BY_FIELD_ID"],  # 按单元分组
        "fields": [
            "ad_id",      # 单元ID
            "ad_name",    # 单元名称
            "status"      # 状态
        ]
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        data = resp.json()
        
        print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if data.get('code') == 0:
            print("✓ 报表 API 调用成功")
            return True
        else:
            print(f"❌ 调用失败: {data.get('message')}")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

if __name__ == '__main__':
    print("=" * 50)
    print("巨量引擎 API 测试")
    print("=" * 50 + "\n")
    
    token = get_access_token()
    
    if token:
        test_report_api(token)
    else:
        print("\n⚠️  无法获取访问令牌，请检查：")
        print("1. App ID 和 Secret 是否正确")
        print("2. 应用是否已审核通过")
        print("3. 是否需要先完成授权流程")
        print("\n建议：把官方配置教程发给我，我根据文档调整")
