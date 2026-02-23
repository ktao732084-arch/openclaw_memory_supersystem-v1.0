#!/usr/bin/env python3
"""
巨量引擎 Access Token 自动续期管理
"""
import requests
import json
from datetime import datetime, timedelta
import os
import sys

# 配置文件路径
TOKEN_FILE = "/root/.openclaw/workspace/douyin-laikedata-feishu/.token_cache.json"

# 巨量引擎配置
APP_ID = 1856818099350592
APP_SECRET = os.getenv('JULIANG_APP_SECRET')

# 导入通知器（可选）
try:
    sys.path.insert(0, os.path.dirname(__file__))
    from notifier import Notifier
    
    # 从环境变量读取 Webhook URL
    FEISHU_WEBHOOK_URL = os.getenv('FEISHU_WEBHOOK_URL', '')
    notifier = Notifier(FEISHU_WEBHOOK_URL) if FEISHU_WEBHOOK_URL else None
except ImportError:
    notifier = None

def load_token_cache():
    """加载缓存的 token 信息"""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  读取 token 缓存失败: {e}")
    return None

def save_token_cache(token_data):
    """保存 token 信息到缓存（增强版）"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        
        # 写入临时文件
        temp_file = TOKEN_FILE + '.tmp'
        with open(temp_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        # 原子性重命名
        os.replace(temp_file, TOKEN_FILE)
        
        print(f"✓ Token 已缓存到: {TOKEN_FILE}")
        
        # 验证保存
        with open(TOKEN_FILE, 'r') as f:
            saved_data = json.load(f)
            if saved_data.get('access_token') != token_data.get('access_token'):
                print(f"⚠️  警告: Token 保存验证失败！")
                return False
        
        print(f"✓ Token 保存验证成功")
        return True
        
    except Exception as e:
        print(f"❌ 保存 token 缓存失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def refresh_access_token(refresh_token):
    """使用 refresh_token 刷新 access_token"""
    print("🔄 正在刷新 Access Token...")
    
    url = "https://api.oceanengine.com/open_api/oauth2/refresh_token/"
    
    payload = {
        "app_id": APP_ID,
        "secret": APP_SECRET,
        "refresh_token": refresh_token
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        
        if data.get('code') == 0:
            token_info = data.get('data', {})
            
            # 计算过期时间
            expires_in = token_info.get('expires_in', 86400)  # 默认24小时
            refresh_expires_in = token_info.get('refresh_token_expires_in', 2592000)  # 默认30天
            
            now = datetime.now()
            
            token_data = {
                "access_token": token_info.get('access_token'),
                "refresh_token": token_info.get('refresh_token'),
                "expires_at": (now + timedelta(seconds=expires_in)).isoformat(),
                "refresh_expires_at": (now + timedelta(seconds=refresh_expires_in)).isoformat(),
                "updated_at": now.isoformat()
            }
            
            print(f"✅ Access Token 刷新成功！")
            print(f"   新 Access Token: {token_data['access_token'][:20]}...")
            print(f"   过期时间: {token_data['expires_at']}")
            
            return token_data
        else:
            error_msg = data.get('message', '未知错误')
            print(f"❌ 刷新失败: {error_msg}")
            
            # 发送通知
            if notifier:
                notifier.notify_token_refresh_failed(error_msg)
            
            return None
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ 刷新异常: {error_msg}")
        
        # 发送通知
        if notifier:
            notifier.notify_token_refresh_failed(error_msg)
        
        return None

def get_valid_token():
    """获取有效的 Access Token（自动续期）"""
    # 1. 尝试从缓存加载
    cache = load_token_cache()
    
    if cache:
        # 兼容两种格式：时间戳和ISO格式
        expires_at_value = cache['expires_at']
        if isinstance(expires_at_value, (int, float)):
            expires_at = datetime.fromtimestamp(expires_at_value)
        else:
            expires_at = datetime.fromisoformat(expires_at_value)
        
        now = datetime.now()
        
        # 如果 token 还有超过1小时有效期，直接使用
        if expires_at > now + timedelta(hours=1):
            remaining = (expires_at - now).total_seconds() / 3600
            print(f"✓ 使用缓存的 Access Token（剩余 {remaining:.1f} 小时）")
            return cache['access_token']
        
        # 如果即将过期，尝试刷新
        print(f"⚠️  Access Token 即将过期（剩余 {(expires_at - now).total_seconds() / 3600:.1f} 小时），开始刷新...")
        
        refresh_token = cache.get('refresh_token')
        if refresh_token:
            new_token_data = refresh_access_token(refresh_token)
            
            if new_token_data:
                save_success = save_token_cache(new_token_data)
                if not save_success:
                    print("⚠️  Token 刷新成功但保存失败，本次仍可使用新 token")
                return new_token_data['access_token']
            else:
                print("❌ Token 刷新失败")
        else:
            print("❌ 缓存中没有 refresh_token")
    
    # 2. 如果缓存不存在或刷新失败，需要手动重新授权
    print("\n" + "="*60)
    print("❌ 无法自动获取 Access Token")
    print("="*60)
    print("\n需要重新授权，请按以下步骤操作：")
    print("\n1. 访问授权页面:")
    print(f"   https://ad.oceanengine.com/openapi/audit/oauth.html?app_id={APP_ID}&state=your_state&scope=4,100000014")
    print("\n2. 授权后获取 auth_code")
    print("\n3. 运行: python3 get_token.py <auth_code>")
    print("\n或者手动更新 .env 文件中的 JULIANG_ACCESS_TOKEN 和 JULIANG_REFRESH_TOKEN")
    print("="*60)
    
    return None

def check_token_status():
    """检查当前 token 状态"""
    print("="*60)
    print("巨量引擎 Token 状态检查")
    print("="*60 + "\n")
    
    cache = load_token_cache()
    
    if not cache:
        print("❌ 未找到 token 缓存")
        print("\n请先运行初始化:")
        print("   python3 init_token.py")
        return
    
    now = datetime.now()
    
    # 兼容两种格式
    expires_at_value = cache['expires_at']
    if isinstance(expires_at_value, (int, float)):
        expires_at = datetime.fromtimestamp(expires_at_value)
    else:
        expires_at = datetime.fromisoformat(expires_at_value)
    
    # refresh_expires_at 可能不存在
    if 'refresh_expires_at' in cache:
        refresh_expires_at_value = cache['refresh_expires_at']
        if isinstance(refresh_expires_at_value, (int, float)):
            refresh_expires_at = datetime.fromtimestamp(refresh_expires_at_value)
        else:
            refresh_expires_at = datetime.fromisoformat(refresh_expires_at_value)
        refresh_remaining = (refresh_expires_at - now).total_seconds() / 86400
    else:
        refresh_remaining = None
    
    access_remaining = (expires_at - now).total_seconds() / 3600
    
    print(f"📊 Token 信息:")
    print(f"   Access Token: {cache['access_token'][:20]}...")
    print(f"   过期时间: {cache['expires_at']}")
    print(f"   剩余时间: {access_remaining:.1f} 小时")
    
    if access_remaining < 1:
        print(f"   ⚠️  即将过期！")
    elif access_remaining < 6:
        print(f"   ⚠️  建议刷新")
    else:
        print(f"   ✅ 状态正常")
    
    print(f"\n   Refresh Token: {cache['refresh_token'][:20]}...")
    if refresh_remaining is not None:
        print(f"   过期时间: {cache.get('refresh_expires_at', '未知')}")
        print(f"   剩余时间: {refresh_remaining:.1f} 天")
        
        if refresh_remaining < 7:
            print(f"   ⚠️  即将过期，需要重新授权！")
        else:
            print(f"   ✅ 状态正常")
    else:
        print(f"   状态: 未知（缓存格式较旧）")
    
    if 'updated_at' in cache:
        print(f"\n   最后更新: {cache['updated_at']}")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "status":
            # 查看状态
            check_token_status()
        
        elif command == "refresh":
            # 手动刷新
            cache = load_token_cache()
            if cache and cache.get('refresh_token'):
                new_token = refresh_access_token(cache['refresh_token'])
                if new_token:
                    save_token_cache(new_token)
            else:
                print("❌ 未找到 refresh_token")
        
        elif command == "get":
            # 获取有效 token
            token = get_valid_token()
            if token:
                print(f"\n✅ Access Token: {token}")
            else:
                print("\n❌ 无法获取有效 token")
    else:
        print("用法:")
        print("  python3 token_manager.py status   # 查看状态")
        print("  python3 token_manager.py refresh  # 手动刷新")
        print("  python3 token_manager.py get      # 获取有效token")
