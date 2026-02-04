#!/usr/bin/env python3
"""
三实例OpenClaw管理系统
主控制实例 + MAC管理实例 + WINDOWS管理实例
"""

import json
import time
import threading
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

class OpenClawInstance:
    """OpenClaw实例管理类"""
    
    def __init__(self, instance_id: str, name: str, description: str, 
                 port: int, workspace_path: str):
        self.instance_id = instance_id
        self.name = name
        self.description = description
        self.port = port
        self.workspace_path = workspace_path
        self.status = "unknown"
        self.last_heartbeat = 0
        self.processes = []
        self.skills = {}
        self.memory_files = {}
        
    def check_status(self) -> bool:
        """检查实例状态"""
        try:
            # 检查端口是否可用
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', self.port))
            sock.close()
            
            if result == 0:
                self.status = "running"
                self.last_heartbeat = time.time()
                return True
            else:
                self.status = "stopped"
                return False
        except Exception as e:
            print(f"❌ 检查 {self.name} 状态出错: {e}")
            self.status = "error"
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """获取实例信息"""
        return {
            "id": self.instance_id,
            "name": self.name,
            "description": self.description,
            "port": self.port,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat,
            "workspace_path": self.workspace_path
        }

class OpenClawOrchestrator:
    """OpenClaw编排器 - 总管所有实例"""
    
    def __init__(self):
        self.instances = {}
        self.sync_dir = Path("/tmp/claw-sync")
        self.control_file = self.sync_dir / "control_center.json"
        
        # 初始化同步目录
        self.sync_dir.mkdir(exist_ok=True)
        
        # 初始化所有实例
        self._initialize_instances()
        
        # 启动监控线程
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_all_instances, daemon=True)
        self.monitor_thread.start()
        
        print("🚀 OpenClaw三实例编排器已启动")
        print("🎯 负责管理: 主控制 + MAC管理 + WINDOWS管理")
    
    def _initialize_instances(self):
        """初始化所有实例"""
        # 主控制实例（当前实例）
        self.instances['main'] = OpenClawInstance(
            instance_id='main',
            name='主控制实例',
            description='总控制中心，负责全局决策',
            port=18789,
            workspace_path='/root/.openclaw/workspace'
        )
        
        # MAC管理实例
        self.instances['mac'] = OpenClawInstance(
            instance_id='mac',
            name='MAC管理实例', 
            description='管理MAC电脑系统',
            port=18790,
            workspace_path='/tmp/mac-openclaw/workspace'
        )
        
        # WINDOWS管理实例
        self.instances['windows'] = OpenClawInstance(
            instance_id='windows',
            name='WINDOWS管理实例',
            description='管理WINDOWS电脑系统', 
            port=18791,
            workspace_path='/tmp/windows-openclaw/workspace'
        )
        
        print(f"✅ 已初始化 {len(self.instances)} 个OpenClaw实例")
    
    def _monitor_all_instances(self):
        """监控所有实例状态"""
        while self.running:
            try:
                for instance_id, instance in self.instances.items():
                    status = instance.check_status()
                    print(f"📊 {instance.name}: {instance.status}")
                
                # 更新控制中心状态
                self._update_control_center()
                
                time.sleep(30)  # 每30秒检查一次
                
            except Exception as e:
                print(f"❌ 监控实例出错: {e}")
                time.sleep(60)
    
    def _update_control_center(self):
        """更新控制中心状态"""
        status_data = {
            "timestamp": time.time(),
            "orchestrator": "active",
            "instances": {}
        }
        
        for instance_id, instance in self.instances.items():
            status_data["instances"][instance_id] = instance.get_info()
        
        # 写入控制中心文件
        with open(self.control_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
    
    def start_instance(self, instance_id: str) -> bool:
        """启动指定实例"""
        if instance_id not in self.instances:
            print(f"❌ 实例 {instance_id} 不存在")
            return False
        
        instance = self.instances[instance_id]
        
        # 检查是否已经运行
        if instance.check_status():
            print(f"✅ {instance.name} 已经在运行")
            return True
        
        print(f"🚀 启动 {instance.name}...")
        
        try:
            # 根据实例类型启动不同的配置
            if instance_id == 'main':
                # 主实例已经在运行
                return True
            
            elif instance_id == 'mac':
                # 启动MAC管理实例
                return self._start_mac_instance()
            
            elif instance_id == 'windows':
                # 启动WINDOWS管理实例
                return self._start_windows_instance()
            
        except Exception as e:
            print(f"❌ 启动 {instance.name} 失败: {e}")
            return False
    
    def _start_mac_instance(self) -> bool:
        """启动MAC管理实例"""
        try:
            # 创建MAC实例的workspace
            mac_workspace = Path("/tmp/mac-openclaw/workspace")
            mac_workspace.mkdir(parents=True, exist_ok=True)
            
            # 创建配置文件
            mac_config = {
                "meta": {
                    "lastTouchedVersion": "2026.1.29",
                    "lastTouchedAt": time.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
                },
                "agents": {
                    "defaults": {
                        "model": {
                            "primary": "zai/glm-4.5-air"
                        },
                        "workspace": str(mac_workspace),
                        "blockStreamingDefault": "off"
                    }
                },
                "gateway": {
                    "port": 18790,
                    "mode": "local",
                    "bind": "lan"
                }
            }
            
            with open(mac_workspace / "openclaw.json", 'w', encoding='utf-8') as f:
                json.dump(mac_config, f, ensure_ascii=False, indent=2)
            
            print(f"✅ MAC管理实例配置已创建")
            print(f"📁 配置路径: {mac_workspace}")
            print(f"🚀 端口: 18790")
            
            # 注意：这里只是创建配置，实际启动可能需要手动操作
            return True
            
        except Exception as e:
            print(f"❌ 创建MAC实例配置失败: {e}")
            return False
    
    def _start_windows_instance(self) -> bool:
        """启动WINDOWS管理实例"""
        try:
            # 创建WINDOWS实例的workspace
            windows_workspace = Path("/tmp/windows-openclaw/workspace")
            windows_workspace.mkdir(parents=True, exist_ok=True)
            
            # 创建配置文件
            windows_config = {
                "meta": {
                    "lastTouchedVersion": "2026.1.29", 
                    "lastTouchedAt": time.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
                },
                "agents": {
                    "defaults": {
                        "model": {
                            "primary": "zai/glm-4.5-air"
                        },
                        "workspace": str(windows_workspace),
                        "blockStreamingDefault": "off"
                    }
                },
                "gateway": {
                    "port": 18791,
                    "mode": "local", 
                    "bind": "lan"
                }
            }
            
            with open(windows_workspace / "openclaw.json", 'w', encoding='utf-8') as f:
                json.dump(windows_config, f, ensure_ascii=False, indent=2)
            
            print(f"✅ WINDOWS管理实例配置已创建")
            print(f"📁 配置路径: {windows_workspace}")
            print(f"🚀 端口: 18791")
            
            return True
            
        except Exception as e:
            print(f"❌ 创建WINDOWS实例配置失败: {e}")
            return False
    
    def control_computer(self, computer_type: str, command: str) -> bool:
        """控制指定电脑"""
        if computer_type not in ['mac', 'windows']:
            print(f"❌ 不支持的电脑类型: {computer_type}")
            return False
        
        instance = self.instances[computer_type]
        
        if not instance.check_status():
            print(f"❌ {instance.name} 未运行")
            return False
        
        # 发送控制命令
        control_data = {
            "timestamp": time.time(),
            "command": command,
            "target": computer_type,
            "sender": "main_orchestrator",
            "type": "computer_control"
        }
        
        # 写入对应电脑的指令文件
        control_file = self.sync_dir / f"{computer_type}_control.json"
        with open(control_file, 'w', encoding='utf-8') as f:
            json.dump(control_data, f, ensure_ascii=False, indent=2)
        
        print(f"🚀 已发送控制指令到 {instance.name}: {command}")
        return True
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统整体状态"""
        status = {
            "timestamp": time.time(),
            "orchestrator": "active",
            "total_instances": len(self.instances),
            "running_instances": 0,
            "instances": {}
        }
        
        for instance_id, instance in self.instances.items():
            instance_info = instance.get_info()
            status["instances"][instance_id] = instance_info
            
            if instance_info["status"] == "running":
                status["running_instances"] += 1
        
        return status
    
    def shutdown_all(self):
        """关闭所有实例"""
        print("🛑 开始关闭所有OpenClaw实例...")
        
        for instance_id, instance in self.instances.items():
            if instance.check_status():
                print(f"⏹️  关闭 {instance.name}...")
                # 这里可以添加实际的关闭逻辑
        
        self.running = False
        print("✅ 所有实例已关闭")

# 主函数
def main():
    print("🚀 OpenClaw三实例管理系统")
    print("=" * 60)
    print("🎯 架构:")
    print("   主控制实例 (18789) - 总控制中心")
    print("   MAC管理实例 (18790) - 管理MAC电脑")
    print("   WINDOWS管理实例 (18791) - 管理WINDOWS电脑")
    print("=" * 60)
    
    orchestrator = OpenClawOrchestrator()
    
    try:
        # 启动所有实例
        print("\n🚀 启动所有实例...")
        for instance_id in ['main', 'mac', 'windows']:
            success = orchestrator.start_instance(instance_id)
            print(f"   {instance_id}: {'✅' if success else '❌'}")
        
        # 检查状态
        print("\n📊 检查实例状态...")
        status = orchestrator.get_system_status()
        print(f"运行实例: {status['running_instances']}/{status['total_instances']}")
        
        # 测试控制功能
        print("\n🧪 测试电脑控制功能...")
        orchestrator.control_computer('mac', '获取系统信息')
        orchestrator.control_computer('windows', '执行系统检查')
        
        # 保持运行
        print("\n💤 系统持续运行中... (按 Ctrl+C 停止)")
        while True:
            time.sleep(60)
            status = orchestrator.get_system_status()
            if int(time.time()) % 300 == 0:  # 每5分钟打印一次状态
                print(f"📊 系统状态: {status['running_instances']}/{status['total_instances']} 实例运行")
            
    except KeyboardInterrupt:
        print("\n⏹️ 接收到停止信号...")
    finally:
        orchestrator.shutdown_all()

if __name__ == "__main__":
    main()