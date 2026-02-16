#!/usr/bin/env python3
"""
飞书配置测试脚本
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_feishu_config():
    """测试飞书配置是否正确"""
    print("🔍 开始测试飞书配置...\n")
    
    # 1. 检查环境变量
    app_id = os.getenv('FEISHU_APP_ID')
    app_secret = os.getenv('FEISHU_APP_SECRET')
    app_token = os.getenv('FEISHU_APP_TOKEN')
    table_id = os.getenv('FEISHU_TABLE_ID')
    
    if not all([app_id, app_secret, app_token, table_id]):
        print("❌ 配置不完整，请检查 .env 文件")
        print(f"   App ID: {'✓' if app_id else '✗'}")
        print(f"   App Secret: {'✓' if app_secret else '✗'}")
        print(f"   App Token: {'✓' if app_token else '✗'}")
        print(f"   Table ID: {'✓' if table_id else '✗'}")
        return False
    
    print("✓ 环境变量配置完整\n")
    
    # 2. 测试获取 tenant_access_token
    print("🔑 测试获取访问令牌...")
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": app_id,
        "app_secret": app_secret
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        
        if data.get('code') == 0:
            token = data['tenant_access_token']
            print(f"✓ 成功获取令牌: {token[:20]}...\n")
        else:
            print(f"❌ 获取令牌失败: {data.get('msg')}")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False
    
    # 3. 测试访问多维表格
    print("📊 测试访问多维表格...")
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    params = {"page_size": 1}
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        data = resp.json()
        
        if data.get('code') == 0:
            print("✓ 成功访问多维表格\n")
            print("=" * 50)
            print("✅ 飞书配置正确，可以开始使用！")
            print("=" * 50)
            return True
        else:
            print(f"❌ 访问表格失败: {data.get('msg')}")
            print("\n可能的原因：")
            print("1. 应用未授权给该多维表格（需要在表格中添加机器人）")
            print("2. APP_TOKEN 或 TABLE_ID 不正确")
            print("3. 应用权限不足（需要 bitable:record 权限）")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

if __name__ == '__main__':
    test_feishu_config()
