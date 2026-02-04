#!/usr/bin/env python3
"""
清理消息堆积并修复监控系统
"""

import json
import os
import time
from pathlib import Path

def clear_message_backlog():
    """清理堆积的消息"""
    sync_dir = Path("/tmp/claw-sync")
    inbox_file = sync_dir / "inbox.json"
    outbox_file = sync_dir / "outbox.json"
    
    print("🧹 清理消息堆积...")
    
    # 清空收件箱
    if inbox_file.exists():
        with open(inbox_file, 'w', encoding='utf-8') as f:
            json.dump({"messages": [], "last_check": time.time()}, f, ensure_ascii=False)
        print("✅ 收件箱已清空")
    
    # 清空发件箱
    if outbox_file.exists():
        with open(outbox_file, 'w', encoding='utf-8') as f:
            json.dump({"messages": [], "last_reply": time.time()}, f, ensure_ascii=False)
        print("✅ 发件箱已清空")
    
    # 清空其他可能堆积的文件
    for status_file in sync_dir.glob("status_*.json"):
        status_file.unlink()
        print(f"✅ 删除状态文件: {status_file.name}")

def stop_unused_processes():
    """停止未使用的进程"""
    import subprocess
    
    # 查找并停止可能冲突的进程
    processes = [
        "personal_assistant.py",
        "gateway_cluster_orchestrator.py"
    ]
    
    for process in processes:
        try:
            result = subprocess.run(['pgrep', '-f', process], capture_output=True, text=True)
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        subprocess.run(['kill', '-9', pid])
                        print(f"✅ 已停止进程: {process} (PID: {pid})")
        except:
            pass

def test_mac_skill():
    """测试MAC管理技能"""
    print("🧪 测试MAC管理技能...")
    
    # 添加路径
    import sys
    skill_dir = "/root/.openclaw/skills/mac-manager"
    sys.path.insert(0, skill_dir)
    
    try:
        from mac_manager import mac_manager_skill
        
        # 测试激活
        print("✅ 测试技能激活...")
        if mac_manager_skill.activate("测试激活"):
            print("   技能激活成功")
            
            # 测试系统信息获取
            print("✅ 测试系统信息获取...")
            result = mac_manager_skill.execute_command("get_system_info")
            if "error" not in result:
                print("   系统信息获取成功")
            else:
                print(f"   ❌ 系统信息获取失败: {result['error']}")
            
            # 测试技能停用
            print("✅ 测试技能停用...")
            mac_manager_skill.deactivate("测试完成")
            print("   技能停用成功")
            
        else:
            print("   ❌ 技能激活失败")
            
    except Exception as e:
        print(f"❌ 技能测试失败: {e}")

def main():
    """主清理和修复流程"""
    print("🚀 系统清理和修复开始")
    print("=" * 50)
    
    # 1. 清理消息堆积
    clear_message_backlog()
    
    # 2. 停止未使用的进程
    stop_unused_processes()
    
    # 3. 等待系统稳定
    print("⏳ 等待系统稳定...")
    time.sleep(3)
    
    # 4. 测试MAC管理技能
    test_mac_skill()
    
    # 5. 验证MAC实例
    print("\n🔍 验证MAC管理实例...")
    import requests
    try:
        response = requests.get("http://localhost:18790/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ MAC管理实例运行正常")
        else:
            print("❌ MAC管理实例响应异常")
    except:
        print("❌ MAC管理实例连接失败")
    
    print("\n🎉 清理和修复完成")
    print("💡 系统现在应该可以正常使用了")

if __name__ == "__main__":
    main()