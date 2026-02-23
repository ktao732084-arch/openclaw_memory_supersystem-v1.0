#!/usr/bin/env python3
"""
健康检查脚本 - 检查各组件状态并预警
"""
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

# 配置
TOKEN_CACHE_FILE = Path(__file__).parent / ".token_cache.json"
HEALTH_LOG_FILE = Path(__file__).parent / "health_check.log"

def log(message):
    """日志输出"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{timestamp}] {message}"
    print(line, flush=True)
    
    # 写入日志文件
    with open(HEALTH_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def check_juliang_token():
    """检查巨量引擎 Token 状态"""
    log("=" * 50)
    log("检查巨量引擎 Token...")
    
    if not TOKEN_CACHE_FILE.exists():
        log("❌ Token 缓存文件不存在")
        return {"status": "error", "message": "Token 缓存文件不存在"}
    
    try:
        with open(TOKEN_CACHE_FILE, 'r') as f:
            cache = json.load(f)
        
        access_expires = datetime.fromisoformat(cache['expires_at'])
        refresh_expires = datetime.fromisoformat(cache['refresh_expires_at'])
        now = datetime.now()
        
        access_remaining = access_expires - now
        refresh_remaining = refresh_expires - now
        
        result = {
            "access_token_remaining_hours": access_remaining.total_seconds() / 3600,
            "refresh_token_remaining_days": refresh_remaining.total_seconds() / 86400,
            "access_expires_at": cache['expires_at'],
            "refresh_expires_at": cache['refresh_expires_at']
        }
        
        # 判断状态
        if refresh_remaining.days < 7:
            log(f"⚠️  警告: refresh_token 将在 {refresh_remaining.days} 天后过期！")
            log(f"   需要尽快重新授权巨量引擎")
            result["status"] = "warning"
            result["message"] = f"refresh_token 将在 {refresh_remaining.days} 天后过期"
        elif access_remaining.total_seconds() < 0:
            log("❌ access_token 已过期")
            result["status"] = "error"
            result["message"] = "access_token 已过期"
        else:
            log(f"✅ Token 状态正常")
            log(f"   access_token 剩余: {access_remaining}")
            log(f"   refresh_token 剩余: {refresh_remaining.days} 天")
            result["status"] = "ok"
            result["message"] = "Token 状态正常"
        
        return result
        
    except Exception as e:
        log(f"❌ 检查失败: {e}")
        return {"status": "error", "message": str(e)}

def check_feishu_connection():
    """检查飞书连接"""
    log("=" * 50)
    log("检查飞书连接...")
    
    try:
        import requests
        
        app_id = "cli_a90737e0f5b81cd3"
        app_secret = os.getenv('FEISHU_APP_SECRET')
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        response = requests.post(url, json={
            "app_id": app_id,
            "app_secret": app_secret
        }, timeout=10)
        
        result = response.json()
        
        if result.get('code') == 0:
            log("✅ 飞书连接正常")
            return {"status": "ok", "message": "飞书连接正常"}
        else:
            log(f"❌ 飞书连接失败: {result}")
            return {"status": "error", "message": f"飞书连接失败: {result}"}
            
    except Exception as e:
        log(f"❌ 飞书检查失败: {e}")
        return {"status": "error", "message": str(e)}

def check_juliang_api():
    """检查巨量引擎 API 可用性"""
    log("=" * 50)
    log("检查巨量引擎 API...")
    
    try:
        from token_manager import get_valid_token
        import requests
        
        token = get_valid_token()
        
        # 简单的 API 调用测试
        url = "https://api.oceanengine.com/open_api/2/user/info/"
        response = requests.get(url, headers={"Access-Token": token}, timeout=10)
        result = response.json()
        
        if result.get('code') == 0:
            log("✅ 巨量引擎 API 正常")
            return {"status": "ok", "message": "巨量引擎 API 正常"}
        else:
            log(f"⚠️  巨量引擎 API 响应异常: {result}")
            return {"status": "warning", "message": f"API 响应: {result}"}
            
    except Exception as e:
        log(f"❌ 巨量引擎 API 检查失败: {e}")
        return {"status": "error", "message": str(e)}

def check_sync_script():
    """检查同步脚本"""
    log("=" * 50)
    log("检查同步脚本...")
    
    script_path = Path(__file__).parent / "sync_stable.py"
    
    if not script_path.exists():
        log("❌ sync_stable.py 不存在")
        return {"status": "error", "message": "sync_stable.py 不存在"}
    
    log("✅ sync_stable.py 存在")
    
    # 检查依赖
    try:
        import requests
        from dotenv import load_dotenv
        log("✅ 依赖包正常")
        return {"status": "ok", "message": "脚本和依赖正常"}
    except ImportError as e:
        log(f"❌ 缺少依赖: {e}")
        return {"status": "error", "message": f"缺少依赖: {e}"}

def main():
    log("=" * 50)
    log("健康检查开始")
    log("=" * 50)
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # 执行各项检查
    results["checks"]["juliang_token"] = check_juliang_token()
    results["checks"]["feishu_connection"] = check_feishu_connection()
    results["checks"]["juliang_api"] = check_juliang_api()
    results["checks"]["sync_script"] = check_sync_script()
    
    # 汇总状态
    statuses = [c["status"] for c in results["checks"].values()]
    
    if "error" in statuses:
        results["overall"] = "error"
        summary = "❌ 存在错误，需要立即处理"
    elif "warning" in statuses:
        results["overall"] = "warning"
        summary = "⚠️  存在警告，建议尽快处理"
    else:
        results["overall"] = "ok"
        summary = "✅ 所有检查通过"
    
    log("=" * 50)
    log(f"检查结果: {summary}")
    log("=" * 50)
    
    # 输出 JSON 结果（供程序读取）
    print("\n__JSON_OUTPUT__")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    
    return results

if __name__ == "__main__":
    results = main()
    
    # 如果有错误，退出码为 1
    if results["overall"] == "error":
        sys.exit(1)
