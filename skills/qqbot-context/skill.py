from openclaw.skills.base import BaseSkill
from openclaw.gateway.context import ContextManager
from datetime import datetime, timedelta
import json
import os

class QQBotContextManager(BaseSkill):
    """QQ Bot专用上下文管理器 - 增强版"""
    
    def __init__(self):
        super().__init__()
        
        # 加载架构上下文
        self.architecture_context = self._load_architecture_context()
        
        # QQ Bot专用配置
        self.qqbot_config = {
            'max_context_length': 110000,      # QQ Bot上下文最大长度
            'compression_threshold': 80000,    # 开始压缩的阈值（80K）
            'new_session_threshold': 110000,    # 开新会话的阈值（110K）
            'max_history_messages': 200,       # 最大历史消息数
            'session_timeout': 60,              # 会话超时时间（分钟）
            'auto_compress': True,             # 自动压缩
            'auto_new_session': True,           # 自动开新会话
            'include_architecture': True        # 包含架构上下文
        }
        
        # 会话管理
        self.sessions = {}
        self.current_session = None
        
        # 加载现有会话
        self._load_sessions()
    
    def process(self, message):
        """处理消息并管理QQ Bot上下文"""
        if self._is_qqbot_message(message):
            return self._manage_qqbot_context(message)
        return message
    
    def _load_architecture_context(self):
        """加载架构上下文信息"""
        try:
            context_file = 'qqbot_context/architecture_context.md'
            if os.path.exists(context_file):
                with open(context_file, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                return "# 架构上下文信息尚未加载"
        except Exception as e:
            print(f"加载架构上下文失败: {e}")
            return "# 架构上下文加载失败"
    
    def _is_qqbot_message(self, message):
        """检测QQ Bot消息"""
        if not isinstance(message, str) or len(message.strip()) == 0:
            return False
        
        conditions = [
            "[QQBot" in message,
            "10D3628F6BDE4E5010FA802750E9021C" in message,
            "2026-" in message,
            "GMT+8" in message
        ]
        
        system_prompt_condition = "【系统提示】" in message or "【系统提示" in message
        
        core_match = any(conditions)
        return core_match or system_prompt_condition
    
    def _manage_qqbot_context(self, message):
        """管理QQ Bot上下文 - 包含架构信息"""
        # 获取或创建当前会话
        session = self._get_or_create_session()
        
        # 如果是新会话且需要包含架构信息，添加架构上下文
        if self.qqbot_config['include_architecture'] and len(session['messages']) == 0:
            self._add_architecture_context(session)
        
        # 添加消息到会话
        self._add_message_to_session(session, message)
        
        # 检查上下文状态
        context_info = self._check_context_status(session)
        
        # 根据状态执行相应操作
        if context_info['needs_new_session'] and self.qqbot_config['auto_new_session']:
            return self._start_new_session(message)
        elif context_info['needs_compression'] and self.qqbot_config['auto_compress']:
            return self._compress_context(session, message)
        else:
            return self._update_context_normal(session, message)
    
    def _add_architecture_context(self, session):
        """添加架构上下文到会话"""
        # 添加架构信息作为系统消息
        architecture_message = {
            'content': f"""
=== 系统架构信息 ===
{self.architecture_context}

=== 上下文说明 ===
- 当前使用的是增强版QQ Bot上下文管理系统
- 支持双实例架构（服务器OpenClaw + 本地Moltbot）
- 上下文容量：110K字符
- 压缩阈值：80K字符
- 新会话阈值：110K字符
- 支持架构上下文自动加载

=== 注意事项 ===
- 所有架构信息仅供参考
- 实际实施可能需要调整
- 如需更新架构信息，请修改对应文件
            """,
            'timestamp': datetime.now(),
            'type': 'system_architecture',
            'length': len(self.architecture_context.encode('utf-8'))
        }
        
        session['messages'].append(architecture_message)
        session['context_length'] += architecture_message['length']
        session['has_architecture_context'] = True
        
        print(f"架构上下文已添加到会话 {session['id']}")
    
    def _get_or_create_session(self):
        """获取或创建当前会话"""
        current_time = datetime.now()
        
        # 检查是否有活跃会话
        if self.current_session and self.current_session in self.sessions:
            session = self.sessions[self.current_session]
            
            # 检查会话是否超时
            if (current_time - session['last_activity']).total_seconds() > self.qqbot_config['session_timeout'] * 60:
                # 会话超时，结束并创建新会话
                self._end_session(self.current_session)
                return self._create_new_session()
            else:
                return session
        else:
            # 创建新会话
            return self._create_new_session()
    
    def _create_new_session(self):
        """创建新会话"""
        session_id = f"qqbot_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session = {
            'id': session_id,
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'messages': [],
            'context_length': 0,
            'compression_count': 0,
            'session_number': len(self.sessions) + 1,
            'has_architecture_context': False
        }
        
        self.sessions[session_id] = session
        self.current_session = session_id
        
        return session
    
    def _add_message_to_session(self, session, message):
        """添加消息到会话"""
        # 提取消息内容
        content = self._extract_message_content(message)
        
        # 计算消息长度（简单估算）
        message_length = len(content.encode('utf-8'))
        
        # 添加消息
        message_entry = {
            'content': content,
            'timestamp': datetime.now(),
            'type': 'user' if '【用户输入】' in message else 'system',
            'length': message_length
        }
        
        session['messages'].append(message_entry)
        session['last_activity'] = datetime.now()
        session['context_length'] += message_length
        
        # 限制历史消息数量
        if len(session['messages']) > self.qqbot_config['max_history_messages']:
            # 移除最旧的消息
            removed = session['messages'].pop(0)
            session['context_length'] -= removed['length']
    
    def _check_context_status(self, session):
        """检查上下文状态"""
        return {
            'current_length': session['context_length'],
            'needs_compression': session['context_length'] > self.qqbot_config['compression_threshold'],
            'needs_new_session': session['context_length'] > self.qqbot_config['new_session_threshold'],
            'session_age': (datetime.now() - session['created_at']).total_seconds() / 60,
            'message_count': len(session['messages']),
            'has_architecture': session.get('has_architecture_context', False)
        }
    
    def _compress_context(self, session, current_message):
        """压缩上下文"""
        if session['compression_count'] >= 3:  # 最多压缩3次
            # 达到压缩上限，开启新会话
            return self._start_new_session(current_message)
        
        # 保留最近的重要消息
        important_messages = []
        total_length = 0
        
        # 从后往前遍历，保留重要消息
        for msg in reversed(session['messages']):
            # 如果是架构上下文，跳过压缩
            if msg.get('type') == 'system_architecture':
                important_messages.insert(0, msg)
                total_length += msg['length']
                continue
                
            if total_length < self.qqbot_config['max_context_length'] * 0.6:  # 保留60%的空间
                important_messages.insert(0, msg)
                total_length += msg['length']
            else:
                break
        
        # 更新会话消息
        session['messages'] = important_messages
        session['context_length'] = total_length
        session['compression_count'] += 1
        
        # 记录压缩操作
        compression_record = {
            'timestamp': datetime.now(),
            'original_length': session['context_length'] + sum(msg['length'] for msg in session['messages'][len(important_messages):]),
            'compressed_length': total_length,
            'compression_ratio': total_length / (session['context_length'] + sum(msg['length'] for msg in session['messages'][len(important_messages):]))
        }
        
        if 'compression_history' not in session:
            session['compression_history'] = []
        session['compression_history'].append(compression_record)
        
        return {
            'action': 'compressed',
            'session_id': session['id'],
            'compression_info': compression_record,
            'current_length': total_length,
            'architecture_preserved': session.get('has_architecture_context', False)
        }
    
    def _start_new_session(self, current_message):
        """开启新会话"""
        # 结束当前会话
        if self.current_session in self.sessions:
            self._end_session(self.current_session)
        
        # 创建新会话
        new_session = self._create_new_session()
        
        # 在新会话中添加当前消息
        self._add_message_to_session(new_session, current_message)
        
        return {
            'action': 'new_session',
            'old_session_id': self.current_session,
            'new_session_id': new_session['id'],
            'new_session_number': new_session['session_number'],
            'message': current_message,
            'architecture_loaded': self.qqbot_config['include_architecture']
        }
    
    def _update_context_normal(self, session, message):
        """正常更新上下文"""
        session['last_activity'] = datetime.now()
        return {
            'action': 'normal',
            'session_id': session['id'],
            'context_length': session['context_length'],
            'message_count': len(session['messages']),
            'has_architecture': session.get('has_architecture_context', False)
        }
    
    def _extract_message_content(self, message):
        """提取消息内容"""
        splitters = ["】", "]", "|", "："]
        
        for splitter in splitters:
            if splitter in message:
                parts = message.split(splitter, 1)
                if len(parts) > 1:
                    content = parts[1].strip()
                    # 移除系统提示部分
                    if "【系统提示" in content:
                        content = content.split("【系统提示")[-1].strip()
                    return content
        
        return message.strip()
    
    def _end_session(self, session_id):
        """结束会话"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session['ended_at'] = datetime.now()
            session['total_duration'] = (session['ended_at'] - session['created_at']).total_seconds()
            
            # 保存会话数据
            self._save_session(session)
            
            # 从活跃会话中移除
            del self.sessions[session_id]
            
            if self.current_session == session_id:
                self.current_session = None
    
    def _save_sessions(self):
        """保存会话数据"""
        try:
            sessions_data = {}
            for session_id, session in self.sessions.items():
                # 转换datetime对象为字符串
                session_data = session.copy()
                session_data['created_at'] = session_data['created_at'].isoformat()
                session_data['last_activity'] = session_data['last_activity'].isoformat()
                if 'ended_at' in session_data:
                    session_data['ended_at'] = session_data['ended_at'].isoformat()
                
                # 转换消息中的时间戳
                for msg in session_data['messages']:
                    msg['timestamp'] = msg['timestamp'].isoformat()
                
                sessions_data[session_id] = session_data
            
            with open('qqbot_sessions.json', 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, ensure_ascii=False, indent=2, default=str)
                
        except Exception as e:
            print(f"保存会话数据失败: {e}")
    
    def _load_sessions(self):
        """加载会话数据"""
        try:
            if 'qqbot_sessions.json' in os.listdir():
                with open('qqbot_sessions.json', 'r', encoding='utf-8') as f:
                    sessions_data = json.load(f)
                
                for session_id, session_data in sessions_data.items():
                    # 转换字符串为datetime对象
                    session_data['created_at'] = datetime.fromisoformat(session_data['created_at'])
                    session_data['last_activity'] = datetime.fromisoformat(session_data['last_activity'])
                    
                    # 转换消息中的时间戳
                    for msg in session_data['messages']:
                        msg['timestamp'] = datetime.fromisoformat(msg['timestamp'])
                    
                    self.sessions[session_id] = session_data
                    
                    # 恢复当前会话
                    if session_data.get('is_active', False):
                        self.current_session = session_id
                        
        except Exception as e:
            print(f"加载会话数据失败: {e}")
    
    def get_session_info(self, session_id=None):
        """获取会话信息"""
        if session_id is None:
            session_id = self.current_session
        
        if session_id in self.sessions:
            session = self.sessions[session_id]
            return {
                'session_id': session_id,
                'created_at': session['created_at'],
                'last_activity': session['last_activity'],
                'messages_count': len(session['messages']),
                'context_length': session['context_length'],
                'compression_count': session.get('compression_count', 0),
                'session_number': session.get('session_number', 1),
                'has_architecture': session.get('has_architecture_context', False),
                'architecture_context_length': sum(msg['length'] for msg in session['messages'] if msg.get('type') == 'system_architecture')
            }
        return None
    
    def get_all_sessions(self):
        """获取所有会话信息"""
        sessions_info = {}
        for session_id, session in self.sessions.items():
            sessions_info[session_id] = self.get_session_info(session_id)
        return sessions_info
    
    def update_architecture_context(self, new_context):
        """更新架构上下文"""
        self.architecture_context = new_context
        try:
            with open('qqbot_context/architecture_context.md', 'w', encoding='utf-8') as f:
                f.write(new_context)
            print("架构上下文已更新")
        except Exception as e:
            print(f"更新架构上下文失败: {e}")