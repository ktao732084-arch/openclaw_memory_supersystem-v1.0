#!/usr/bin/env python3
"""
Gateway集群技能集成器
将文件通信功能集成到现有技能系统中
"""

import json
import time
import threading
from pathlib import Path

class GatewayClusterSkill:
    """Gateway集群控制技能"""
    
    def __init__(self):
        self.sync_dir = Path("/tmp/claw-sync")
        self.inbox_file = self.sync_dir / "inbox.json"
        self.outbox_file = self.sync_dir / "outbox.json"
        self.last_check = 0
        
        # 确保目录存在
        self.sync_dir.mkdir(exist_ok=True)
        
        # 启动监控线程
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_messages, daemon=True)
        self.monitor_thread.start()
        
        print("🤖 Gateway集群技能已激活")
    
    def _monitor_messages(self):
        """监控来自电脑端的回复"""
        while self.running:
            try:
                if self.outbox_file.exists():
                    with open(self.outbox_file, 'r', encoding='utf-8') as f:
                        outbox = json.load(f)
                    
                    new_messages = []
                    for msg in outbox.get("messages", []):
                        if msg.get("timestamp", 0) > self.last_check:
                            new_messages.append(msg)
                    
                    if new_messages:
                        print(f"📡 Gateway集群收到 {len(new_messages)} 条消息")
                        for msg in new_messages:
                            self._process_cluster_message(msg)
                        
                        self.last_check = time.time()
                        # 清空已处理的消息
                        outbox["messages"] = []
                        with open(self.outbox_file, 'w', encoding='utf-8') as f:
                            json.dump(outbox, f, ensure_ascii=False, indent=2)
                
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Gateway集群监控出错: {e}")
                time.sleep(5)
    
    def _process_cluster_message(self, message):
        """处理集群消息"""
        sender = message.get("sender", "unknown")
        reply_text = message.get("reply", "")
        action = message.get("action", "unknown")
        status = message.get("status", "unknown")
        
        print(f"🎯 [{sender}] {action} - {status}")
        print(f"💬 {reply_text}")
        
        # 根据消息类型进行特殊处理
        if action == "test_ack":
            print("✅ Gateway集群测试成功")
        elif action == "heartbeat_response":
            print("💓 Gateway连接状态正常")
        elif action == "file_info":
            print(f"📁 文件信息: {reply_text}")
    
    def send_to_personal_assistant(self, message, action="general"):
        """发送消息到个人助手"""
        msg_id = f"cluster_{int(time.time() * 1000)}"
        
        message_data = {
            "id": msg_id,
            "timestamp": time.time(),
            "target": "personal-assistant",
            "sender": "gateway-cluster",
            "message": message,
            "type": "cluster_command",
            "action": action,
            "source_skill": "gateway-cluster"
        }
        
        # 读取收件箱
        if self.inbox_file.exists():
            with open(self.inbox_file, 'r', encoding='utf-8') as f:
                inbox = json.load(f)
        else:
            inbox = {"messages": [], "last_check": 0}
        
        # 添加消息
        inbox["messages"].append(message_data)
        inbox["last_check"] = time.time()
        
        # 写回文件
        with open(self.inbox_file, 'w', encoding='utf-8') as f:
            json.dump(inbox, f, ensure_ascii=False, indent=2)
        
        print(f"🚀 已发送到个人助手: {message[:50]}...")
        return msg_id
    
    def execute_remote_command(self, command, params=None):
        """执行远程命令"""
        if params is None:
            params = {}
        
        # 根据命令类型构建消息
        if command == "system_info":
            message = f"获取系统信息: {params}"
            action = "system_info"
        elif command == "file_operation":
            message = f"执行文件操作: {params}"
            action = "file_operation"
        elif command == "task_execution":
            message = f"执行任务: {params}"
            action = "task_execution"
        else:
            message = f"执行命令: {command} - {params}"
            action = "general"
        
        return self.send_to_personal_assistant(message, action)
    
    def check_cluster_status(self):
        """检查集群状态"""
        status = {
            "main_gateway": "active",
            "personal_assistant": "unknown",
            "communication": "file_based",
            "last_activity": self.last_check,
            "sync_dir": str(self.sync_dir),
            "inbox_exists": self.inbox_file.exists(),
            "outbox_exists": self.outbox_file.exists()
        }
        
        if self.outbox_file.exists():
            try:
                with open(self.outbox_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        outbox = json.loads(content)
                        status["pending_replies"] = len(outbox.get("messages", []))
                    else:
                        status["pending_replies"] = 0
            except Exception as e:
                print(f"❌ 读取outbox文件出错: {e}")
                status["pending_replies"] = 0
        
        return status
    
    def shutdown(self):
        """关闭技能"""
        self.running = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=2)
        print("🔌 Gateway集群技能已关闭")

# 技能接口函数
def gateway_cluster_skill():
    """Gateway集群技能入口函数"""
    skill = GatewayClusterSkill()
    
    # 注册技能命令处理器
    def handle_cluster_command(command, params=None):
        if command == "send":
            return skill.send_to_personal_assistant(params or "默认消息")
        elif command == "status":
            status = skill.check_cluster_status()
            return json.dumps(status, indent=2, ensure_ascii=False)
        elif command == "system_info":
            return skill.execute_remote_command("system_info", params)
        elif command == "file_op":
            return skill.execute_remote_command("file_operation", params)
        else:
            return f"未知命令: {command}"
    
    return {
        "name": "Gateway集群控制",
        "description": "控制和管理电脑端个人助手",
        "commands": {
            "send": "发送消息到个人助手",
            "status": "检查集群状态",
            "system_info": "获取系统信息",
            "file_op": "执行文件操作"
        },
        "handle_command": handle_cluster_command
    }

# 测试函数
def test_gateway_cluster():
    """测试Gateway集群技能"""
    print("🧪 测试Gateway集群技能...")
    
    skill = GatewayClusterSkill()
    
    # 测试状态检查
    print("\n📊 检查集群状态...")
    status = skill.check_cluster_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    # 测试发送消息
    print("\n📤 发送测试消息...")
    msg_id = skill.send_to_personal_assistant(
        "这是一条来自Gateway集群技能的测试消息"
    )
    print(f"消息ID: {msg_id}")
    
    # 等待回复
    print("\n⏳ 等待回复...")
    time.sleep(5)
    
    # 再次检查状态
    print("\n📊 再次检查集群状态...")
    status = skill.check_cluster_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    skill.shutdown()
    print("\n✅ 测试完成")

if __name__ == "__main__":
    test_gateway_cluster()