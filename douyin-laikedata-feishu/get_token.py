#!/usr/bin/env python3
"""
获取巨量引擎 Access Token
"""
import requests
import json

JULIANG_APP_ID = 1856818099350592
JULIANG_SECRET = "REDACTED"
AUTH_CODE = "REDACTED"

def get_access_token():
    """使用 auth_code 换取 access_token"""
    print("🔑 使用 auth_code 换取 Access Token...")
    
    url = "https://api.oceanengine.com/open_api/oauth2/access_token/"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "app_id": JULIANG_APP_ID,
        "secret": JULIANG_SECRET,
        "auth_code": AUTH_CODE
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        data = resp.json()
        
        print(f"\n响应:\n{json.dumps(data, indent=2, ensure_ascii=False)}\n")
        
        if data.get('code') == 0:
            access_token = data['data']['access_token']
            refresh_token = data['data']['refresh_token']
            expires_in = data['data']['expires_in']
            
            print("=" * 50)
            print("✅ Access Token 获取成功！")
            print("=" * 50)
            print(f"Access Token: {access_token}")
            print(f"Refresh Token: {refresh_token}")
            print(f"有效期: {expires_in} 秒 ({expires_in/3600:.1f} 小时)")
            print("=" * 50)
            
            # 保存到文件
            with open('.juliang_token', 'w') as f:
                json.dump({
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'expires_in': expires_in
                }, f, indent=2)
            
            print("\n✓ Token 已保存到 .juliang_token 文件")
            return access_token
        else:
            print(f"❌ 获取失败: {data.get('message')}")
            print(f"   错误码: {data.get('code')}")
            return None
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    get_access_token()
