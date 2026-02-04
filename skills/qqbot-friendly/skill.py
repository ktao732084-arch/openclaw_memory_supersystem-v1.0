from openclaw.skills.base import BaseSkill

class QQBotDetectionSkill(BaseSkill):
    """QQ Bot检测技能 - 仅用于准确识别，不改变原有回复"""
    
    def __init__(self):
        super().__init__()
        self.qqbot_messages = []  # 记录QQ Bot消息
    
    def process(self, message):
        """处理消息 - 仅检测，不修改回复"""
        # 检测是否来自QQ Bot
        is_qqbot = self._is_qqbot_message(message)
        
        if is_qqbot:
            self.qqbot_messages.append({
                'message': message,
                'timestamp': self.get_current_time(),
                'original_content': self._extract_original_content(message)
            })
            # 返回原消息，不进行任何修改
            return message
        else:
            return message
    
    def _is_qqbot_message(self, message):
        """精准的QQ Bot检测逻辑"""
        if not isinstance(message, str) or len(message.strip()) == 0:
            return False
        
        # 核心检测条件
        conditions = [
            "[QQBot" in message,           # 必须包含QQBot标识
            "10D3628F6BDE4E5010FA802750E9021C" in message,  # 包含你的QQ Bot ID
            "2026-" in message,           # 包含年份（时间戳特征）
            "GMT+8" in message or "GMT+8" in message  # 时区特征
        ]
        
        # 或者包含系统提示（辅助检测）
        system_prompt_condition = "【系统提示】" in message or "【系统提示" in message
        
        # 满足核心条件中的任意一个，或者系统提示条件
        core_match = any(conditions)
        
        return core_match or system_prompt_condition
    
    def _extract_original_content(self, message):
        """提取原始内容 - 仅用于记录"""
        splitters = ["】", "]", "|", "："]
        
        for splitter in splitters:
            if splitter in message:
                parts = message.split(splitter, 1)
                if len(parts) > 1:
                    content = parts[1].strip()
                    if "【系统提示】" in content:
                        # 移除系统提示部分，保留实际内容
                        content = content.split("【系统提示")[-1].strip()
                    return content
        
        return message.strip()
    
    def get_qqbot_messages(self):
        """获取检测到的QQ Bot消息"""
        return self.qqbot_messages
    
    def clear_qqbot_messages(self):
        """清空记录"""
        self.qqbot_messages.clear()
    
    def get_current_time(self):
        """获取当前时间"""
        from datetime import datetime
        return datetime.now().isoformat()

# 全局实例用于检测
_qqbot_detector = QQBotDetectionSkill()

def is_qqbot_message(message):
    """全局检测函数"""
    return _qqbot_detector._is_qqbot_message(message)

def extract_qqbot_content(message):
    """全局内容提取函数"""
    return _qqbot_detector._extract_original_content(message)