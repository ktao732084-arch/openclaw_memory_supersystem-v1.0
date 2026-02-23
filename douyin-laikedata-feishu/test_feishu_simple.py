#!/usr/bin/env python3
"""
飞书配置测试脚本（无需 dotenv）
"""
import requests

# 直接配置
FEISHU_APP_ID = "cli_a90737e0f5b81cd3"
FEISHU_APP_SECRET = os.getenv('FEISHU_APP_SECRET')
FEISHU_APP_TOKEN = "FEiCbGEDHarzyUsPG8QcoLxwn7d"
FEISHU_TABLE_ID = "tbl1n1PC1aooYdKk"

def test_feishu_config():
    """测试飞书配置是否正确"""
    print("🔍 开始测试飞书配置...\n")
    
    # 1. 测试获取 tenant_access_token
    print("🔑 测试获取访问令牌...")
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        
        if data.get('code') == 0:
            token = data['tenant_access_token']
            print(f"✓ 成功获取令牌: {token[:20]}...\n")
        else:
            print(f"❌ 获取令牌失败: {data.get('msg')}")
            print(f"   错误码: {data.get('code')}")
            return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False
    
    # 2. 测试访问多维表格
    print("📊 测试访问多维表格...")
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
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
            
            # 显示表格字段信息
            if data.get('data', {}).get('items'):
                print("📋 表格字段预览：")
                fields = data['data']['items'][0].get('fields', {})
                for key in fields.keys():
                    print(f"   - {key}")
            
            print("\n" + "=" * 50)
            print("✅ 飞书配置正确，可以开始使用！")
            print("=" * 50)
            return True
        else:
            print(f"❌ 访问表格失败: {data.get('msg')}")
            print(f"   错误码: {data.get('code')}")
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
