#!/usr/bin/env python3
"""
测试 Token 自动刷新功能
"""
import json
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '/root/.openclaw/workspace/douyin-laikedata-feishu')
from token_manager import get_valid_token, save_token_cache, load_token_cache

def test_token_refresh():
    """测试 token 刷新功能"""
    print("="*60)
    print("测试 Token 自动刷新")
    print("="*60 + "\n")
    
    # 1. 查看当前状态
    print("1️⃣ 当前 Token 状态:")
    cache = load_token_cache()
    if cache:
        expires_at = datetime.fromisoformat(cache['expires_at'])
        now = datetime.now()
        remaining = (expires_at - now).total_seconds() / 3600
        print(f"   剩余时间: {remaining:.1f} 小时\n")
    
    # 2. 模拟 token 即将过期（修改缓存）
    print("2️⃣ 模拟 Token 即将过期（30分钟后过期）...")
    
    if cache:
        # 修改过期时间为30分钟后
        now = datetime.now()
        cache['expires_at'] = (now + timedelta(minutes=30)).isoformat()
        save_token_cache(cache)
        print("   ✓ 已修改缓存\n")
    
    # 3. 测试自动刷新
    print("3️⃣ 测试自动获取 Token（应该触发刷新）...")
    token = get_valid_token()
    
    if token:
        print(f"\n✅ 成功获取 Token: {token[:20]}...\n")
        
        # 4. 查看刷新后的状态
        print("4️⃣ 刷新后的 Token 状态:")
        new_cache = load_token_cache()
        if new_cache:
            new_expires_at = datetime.fromisoformat(new_cache['expires_at'])
            new_remaining = (new_expires_at - datetime.now()).total_seconds() / 3600
            print(f"   新的剩余时间: {new_remaining:.1f} 小时")
            print(f"   ✅ Token 已成功刷新！")
    else:
        print("\n❌ Token 刷新失败")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    test_token_refresh()
