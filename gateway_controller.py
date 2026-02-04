#!/usr/bin/env python3
"""
Gateway集群控制器 - 文件通信方案
由于API返回HTML而非JSON，采用文件通信方式实现控制
"""

import os
import json
import time
import threading
from pathlib import Path

# 通信路径配置
SYNC_DIR = Path("/tmp/claw-sync")
INBOX_FILE = SYNC_DIR / "inbox.json"
OUTBOX_FILE = SYNC_DIR / "outbox.json"
HEARTBEAT_FILE = SYNC_DIR / "heartbeat.json"

class GatewayController:
    def __init__(self):
        # 确保同步目录存在
        SYNC_DIR.mkdir(exist_ok=True)
        
        # 初始化文件
        self._init_files()
        
        # 启动监控线程
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_outbox, daemon=True)
        self._monitor_thread.start()
        
        print("🚀 Gateway集群控制器已启动")
        print(f"📁 通信目录: {SYNC_DIR}")
        print(f"📥 收件箱: {INBOX_FILE}")
        print(f"📤 发件箱: {OUTBOX_FILE}")
    
    def _init_files(self):
        """初始化通信文件"""
        if not INBOX_FILE.exists():
            with open(INBOX_FILE, 'w', encoding='utf-8') as f:
                json.dump({"messages": [], "last_check": time.time()}, f, ensure_ascii=False)
        
        if not OUTBOX_FILE.exists():
            with open(OUTBOX_FILE, 'w', encoding='utf-8') as f:
                json.dump({"messages": [], "last_reply": time.time()}, f, ensure_ascii=False)
        
        if not HEARTBEAT_FILE.exists():
            with open(HEARTBEAT_FILE, 'w', encoding='utf-8') as f:
                json.dump({"status": "active", "last_heartbeat": time.time()}, f, ensure_ascii=False)
    
    def send_to_gateway(self, message, target="personal-assistant"):
        """发送消息到电脑端Gateway"""
        msg_id = f"msg_{int(time.time() * 1000)}"
        
        message_data = {
            "id": msg_id,
            "timestamp": time.time(),
            "target": target,
            "sender": "main-gateway",
            "message": message,
            "type": "command"
        }
        
        # 读取当前收件箱
        with open(INBOX_FILE, 'r', encoding='utf-8') as f:
            inbox = json.load(f)
        
        # 添加新消息
        inbox["messages"].append(message_data)
        inbox["last_check"] = time.time()
        
        # 写回文件
        with open(INBOX_FILE, 'w', encoding='utf-8') as f:
            json.dump(inbox, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已发送消息到Gateway: {message[:50]}...")
        print(f"📋 消息ID: {msg_id}")
        print(f"🎯 目标: {target}")
        
        return msg_id
    
    def get_replies(self):
        """从Gateway获取回复"""
        if not OUTBOX_FILE.exists():
            return []
        
        try:
            with open(OUTBOX_FILE, 'r', encoding='utf-8') as f:
                outbox = json.load(f)
            
            # 检查是否有新回复
            last_check = getattr(self, '_last_reply_check', 0)
            new_replies = []
            
            for msg in outbox["messages"]:
                if msg["timestamp"] > last_check:
                    new_replies.append(msg)
            
            self._last_reply_check = time.time()
            
            if new_replies:
                print(f"📥 收到 {len(new_replies)} 条新回复")
                for reply in new_replies:
                    print(f"   {reply['sender']}: {reply['reply'][:50]}...")
            
            return new_replies
            
        except Exception as e:
            print(f"❌ 读取回复时出错: {e}")
            return []
    
    def _monitor_outbox(self):
        """监控发件箱，处理来自Gateway的消息"""
        while self._running:
            try:
                self.get_replies()
                time.sleep(1)  # 每秒检查一次
            except Exception as e:
                print(f"❌ 监控线程出错: {e}")
                time.sleep(5)
    
    def send_heartbeat(self):
        """发送心跳信号"""
        with open(HEARTBEAT_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "status": "active", 
                "last_heartbeat": time.time(),
                "gateway_info": {
                    "type": "main-gateway",
                    "control_range": "full"
                }
            }, f, ensure_ascii=False)
        
        print("💓 心跳信号已发送")
    
    def shutdown(self):
        """关闭控制器"""
        self._running = False
        if hasattr(self, '_monitor_thread'):
            self._monitor_thread.join(timeout=2)
        print("🔌 Gateway控制器已关闭")

def test_communication():
    """测试通信功能"""
    print("🧪 测试Gateway文件通信...")
    
    controller = GatewayController()
    
    # 发送测试消息
    print("\n📤 发送测试消息...")
    msg_id = controller.send_to_gateway(
        "这是一条来自主Gateway的测试消息，请回复确认收到",
        "personal-assistant"
    )
    
    # 发送心跳
    print("\n💓 发送心跳...")
    controller.send_heartbeat()
    
    # 等待回复
    print("\n⏳ 等待回复...")
    time.sleep(3)
    
    replies = controller.get_replies()
    
    if replies:
        print("✅ 通信测试成功！")
        return True
    else:
        print("⚠️  暂无回复，但通信通道已建立")
        print("💡 电脑端Gateway需要配置相应的文件监控脚本")
        return False

if __name__ == "__main__":
    print("🚀 Gateway集群文件通信控制器")
    print("=" * 60)
    
    success = test_communication()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 通信测试完成，Gateway集群控制方案可行")
    else:
        print("🔧 需要在电脑端配置文件监控脚本")
    
    print("\n📋 下一步:")
    print("1. 在电脑端创建文件监控脚本")
    print("2. 配置自动回复机制")
    print("3. 实现双向通信协议")
    print("4. 集成到现有技能系统")