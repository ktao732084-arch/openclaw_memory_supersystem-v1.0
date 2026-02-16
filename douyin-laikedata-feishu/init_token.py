#!/usr/bin/env python3
"""
初始化 Token 缓存
"""
import json
from datetime import datetime, timedelta

# 当前的 token 信息
CURRENT_ACCESS_TOKEN = "REDACTED"
CURRENT_REFRESH_TOKEN = "REDACTED"

# Token 是在 2026-02-12 20:00 左右获取的，有效期24小时
TOKEN_OBTAINED_AT = datetime(2026, 2, 12, 20, 0, 0)

def init_token_cache():
    """初始化 token 缓存"""
    print("🔧 初始化 Token 缓存...\n")
    
    # 计算过期时间
    access_expires_at = TOKEN_OBTAINED_AT + timedelta(hours=24)
    refresh_expires_at = TOKEN_OBTAINED_AT + timedelta(days=30)
    
    token_data = {
        "access_token": CURRENT_ACCESS_TOKEN,
        "refresh_token": CURRENT_REFRESH_TOKEN,
        "expires_at": access_expires_at.isoformat(),
        "refresh_expires_at": refresh_expires_at.isoformat(),
        "updated_at": TOKEN_OBTAINED_AT.isoformat()
    }
    
    # 保存到文件
    cache_file = "/root/.openclaw/workspace/douyin-laikedata-feishu/.token_cache.json"
    
    with open(cache_file, 'w') as f:
        json.dump(token_data, f, indent=2)
    
    print(f"✅ Token 缓存已创建: {cache_file}\n")
    print(f"📊 Token 信息:")
    print(f"   Access Token: {CURRENT_ACCESS_TOKEN[:20]}...")
    print(f"   过期时间: {access_expires_at}")
    print(f"   Refresh Token: {CURRENT_REFRESH_TOKEN[:20]}...")
    print(f"   过期时间: {refresh_expires_at}")
    
    # 计算剩余时间
    now = datetime.now()
    access_remaining = (access_expires_at - now).total_seconds() / 3600
    
    print(f"\n⏰ 当前剩余时间: {access_remaining:.1f} 小时")
    
    if access_remaining < 1:
        print("   ⚠️  即将过期，建议立即刷新！")
    elif access_remaining < 6:
        print("   ⚠️  建议尽快刷新")
    else:
        print("   ✅ 状态正常")

if __name__ == '__main__':
    init_token_cache()
