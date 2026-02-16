#!/usr/bin/env python3
"""
使用新的auth_code获取access_token
"""
import requests
import json

APP_ID = 1856818099350592
APP_SECRET = "REDACTED"
AUTH_CODE = "REDACTED"

def get_new_token():
    """获取新的access_token"""
    
    url = "https://api.oceanengine.com/open_api/oauth2/access_token/"
    
    payload = {
        "app_id": APP_ID,
        "secret": APP_SECRET,
        "grant_type": "auth_code",
        "auth_code": AUTH_CODE
    }
    
    print("📊 使用新auth_code获取token...")
    print(f"   Auth Code: {AUTH_CODE}")
    print()
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        
        print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
        print()
        
        if data.get('code') == 0:
            token_data = data['data']
            
            print("=" * 60)
            print("✅ 获取Token成功！")
            print("=" * 60)
            print(f"Access Token: {token_data['access_token']}")
            print(f"Refresh Token: {token_data['refresh_token']}")
            print(f"有效期: {token_data['expires_in']} 秒 ({token_data['expires_in']//3600} 小时)")
            print()
            
            # 保存到.env文件
            env_content = f"""# 巨量引擎配置
OCEAN_APP_ID={APP_ID}
OCEAN_APP_SECRET={APP_SECRET}
OCEAN_ACCESS_TOKEN={token_data['access_token']}
OCEAN_REFRESH_TOKEN={token_data['refresh_token']}
OCEAN_EXPIRES_IN={token_data['expires_in']}

# 账户ID
ADVERTISER_ID=1769665409798152
LOCAL_ACCOUNT_ID=1835880409219083

# 飞书配置
FEISHU_APP_ID=cli_a90737e0f5b81cd3
FEISHU_APP_SECRET=REDACTED
FEISHU_APP_TOKEN=FEiCbGEDHarzyUsPG8QcoLxwn7d
FEISHU_TABLE_ID=tbl1n1PC1aooYdKk
"""
            
            with open('.env', 'w') as f:
                f.write(env_content)
            
            print("💾 已保存到 .env 文件")
            
            # 更新token缓存
            import time
            cache = {
                "access_token": token_data['access_token'],
                "refresh_token": token_data['refresh_token'],
                "expires_at": int(time.time()) + token_data['expires_in']
            }
            
            with open('.token_cache.json', 'w') as f:
                json.dump(cache, f, indent=2)
            
            print("💾 已更新 .token_cache.json")
            
            return token_data
        else:
            print(f"❌ 失败: {data.get('message')}")
            return None
            
    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    get_new_token()
