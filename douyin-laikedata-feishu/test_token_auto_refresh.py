#!/usr/bin/env python3
"""
测试 Token 自动刷新机制
"""
import json
from datetime import datetime, timedelta
from token_manager import get_valid_token, save_token_cache, load_token_cache

def test_auto_refresh():
    """测试自动刷新"""
    print("="*60)
    print("Token 自动刷新机制测试")
    print("="*60 + "\n")
    
    # 1. 测试正常获取
    print("1️⃣ 测试正常获取 Token...")
    token = get_valid_token()
    if token:
        print(f"   ✅ 成功: {token[:20]}...\n")
    else:
        print(f"   ❌ 失败\n")
        return
    
    # 2. 模拟即将过期的场景
    print("2️⃣ 模拟 Token 即将过期（30分钟后）...")
    cache = load_token_cache()
    if cache:
        # 修改过期时间为30分钟后
        now = datetime.now()
        cache['expires_at'] = (now + timedelta(minutes=30)).isoformat()
        
        # 保存修改后的缓存
        save_token_cache(cache)
        print("   ✅ 已修改缓存，过期时间设为30分钟后\n")
        
        # 3. 再次获取，应该触发自动刷新
        print("3️⃣ 再次获取 Token（应触发自动刷新）...")
        new_token = get_valid_token()
        if new_token:
            print(f"   ✅ 成功刷新: {new_token[:20]}...\n")
            
            # 验证新 token 的有效期
            new_cache = load_token_cache()
            expires_at = datetime.fromisoformat(new_cache['expires_at'])
            remaining = (expires_at - datetime.now()).total_seconds() / 3600
            print(f"   ✅ 新 Token 有效期: {remaining:.1f} 小时\n")
        else:
            print(f"   ❌ 刷新失败\n")
    else:
        print("   ❌ 无法加载缓存\n")
    
    print("="*60)
    print("测试完成")
    print("="*60)

if __name__ == '__main__':
    test_auto_refresh()
