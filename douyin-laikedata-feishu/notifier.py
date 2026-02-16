#!/usr/bin/env python3
"""
失败通知模块
支持飞书机器人消息推送
"""
import requests
import json
from datetime import datetime

class Notifier:
    """通知器"""
    
    def __init__(self, webhook_url=None):
        """
        初始化通知器
        
        Args:
            webhook_url: 飞书机器人 Webhook URL
        """
        self.webhook_url = webhook_url
    
    def send_feishu_message(self, title, content, msg_type="error"):
        """
        发送飞书消息
        
        Args:
            title: 消息标题
            content: 消息内容（支持列表或字符串）
            msg_type: 消息类型 (error/warning/success/info)
        """
        if not self.webhook_url:
            print("⚠️  未配置飞书 Webhook，跳过通知")
            return False
        
        # 消息类型对应的颜色和图标
        type_config = {
            "error": {"color": "red", "icon": "❌"},
            "warning": {"color": "orange", "icon": "⚠️"},
            "success": {"color": "green", "icon": "✅"},
            "info": {"color": "blue", "icon": "ℹ️"}
        }
        
        config = type_config.get(msg_type, type_config["info"])
        
        # 构建消息内容
        if isinstance(content, list):
            content_text = "\n".join([f"• {item}" for item in content])
        else:
            content_text = content
        
        # 构建富文本消息
        message = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"{config['icon']} {title}"
                    },
                    "template": config["color"]
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": content_text
                        }
                    },
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        ]
                    }
                ]
            }
        }
        
        try:
            resp = requests.post(
                self.webhook_url,
                json=message,
                timeout=10
            )
            
            result = resp.json()
            
            if result.get('code') == 0:
                print(f"✓ 飞书通知发送成功")
                return True
            else:
                print(f"⚠️  飞书通知发送失败: {result.get('msg')}")
                return False
                
        except Exception as e:
            print(f"⚠️  发送通知异常: {e}")
            return False
    
    def notify_sync_failed(self, date, error_msg, details=None):
        """
        通知同步失败
        
        Args:
            date: 同步日期
            error_msg: 错误信息
            details: 详细信息（可选）
        """
        title = "数据同步失败"
        
        content = [
            f"**日期**: {date}",
            f"**错误**: {error_msg}"
        ]
        
        if details:
            if isinstance(details, list):
                content.extend(details)
            else:
                content.append(f"**详情**: {details}")
        
        return self.send_feishu_message(title, content, "error")
    
    def notify_token_refresh_failed(self, error_msg):
        """
        通知 Token 刷新失败
        
        Args:
            error_msg: 错误信息
        """
        title = "Token 刷新失败"
        
        content = [
            f"**错误**: {error_msg}",
            "**建议**: 请检查 Refresh Token 是否过期，可能需要重新授权"
        ]
        
        return self.send_feishu_message(title, content, "error")
    
    def notify_data_anomaly(self, date, anomaly_type, details):
        """
        通知数据异常
        
        Args:
            date: 日期
            anomaly_type: 异常类型
            details: 详细信息
        """
        title = "数据异常告警"
        
        content = [
            f"**日期**: {date}",
            f"**异常类型**: {anomaly_type}",
            f"**详情**: {details}"
        ]
        
        return self.send_feishu_message(title, content, "warning")
    
    def notify_sync_success(self, date, record_count, summary=None):
        """
        通知同步成功（可选）
        
        Args:
            date: 同步日期
            record_count: 记录数量
            summary: 摘要信息（可选）
        """
        title = "数据同步成功"
        
        content = [
            f"**日期**: {date}",
            f"**记录数**: {record_count} 条"
        ]
        
        if summary:
            if isinstance(summary, dict):
                for key, value in summary.items():
                    content.append(f"**{key}**: {value}")
            else:
                content.append(f"**摘要**: {summary}")
        
        return self.send_feishu_message(title, content, "success")


def test_notifier():
    """测试通知功能"""
    import os
    from dotenv import load_dotenv
    
    # 加载配置
    load_dotenv()
    webhook_url = os.getenv('FEISHU_WEBHOOK_URL')
    
    if not webhook_url:
        print("❌ 请在 .env 中配置 FEISHU_WEBHOOK_URL")
        return
    
    notifier = Notifier(webhook_url)
    
    print("测试1: 同步失败通知")
    notifier.notify_sync_failed(
        date="2026-02-12",
        error_msg="API 请求超时",
        details=["重试 3 次后仍然失败", "建议检查网络连接"]
    )
    
    print("\n测试2: Token 刷新失败通知")
    notifier.notify_token_refresh_failed("Refresh Token 已过期")
    
    print("\n测试3: 数据异常告警")
    notifier.notify_data_anomaly(
        date="2026-02-12",
        anomaly_type="消耗金额异常",
        details="今日消耗 5000 元，超过平均值 3 倍"
    )
    
    print("\n测试4: 同步成功通知")
    notifier.notify_sync_success(
        date="2026-02-12",
        record_count=4,
        summary={
            "总消耗": "1,234.56 元",
            "总转化": "12 个",
            "平均转化成本": "102.88 元"
        }
    )


if __name__ == '__main__':
    test_notifier()
