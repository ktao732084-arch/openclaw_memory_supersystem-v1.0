# QQ Bot检测技能

## 功能
仅用于**准确识别**消息是否来自QQ Bot，**不改变任何回复内容**。

## 核心检测逻辑
- 🎯 **精准识别** - 基于多个特征条件
- 📝 **完整记录** - 记录QQ Bot消息信息
- 🔧 **零影响** - 完全保持原有回复不变
- 📊 **可查询** - 提供检测历史记录

## 检测条件
必须满足以下条件之一：
1. **标识匹配**：包含 "[QQBot" 和你的QQ Bot ID
2. **时间特征**：包含年份 "2026-" 和时区 "GMT+8"  
3. **系统提示**：包含 "【系统提示" 标识

## 检测特征
- [QQBot 10D3628F6BDE4E5010FA802750E9021C ...]  # 完整标识
- 2026-01-31 ... GMT+8                          # 时间戳特征
- 【系统提示】由于平台限制...                    # 系统提示特征

## 保持不变
- ✅ 完全保持原有回复内容和格式
- ✅ 不做任何消息修改或适配
- ✅ 代码展示完整，不被简化
- ✅ 技术支持不受影响

## 使用方法
技能自动运行，无需配置。可以通过以下方式检测：
```python
from skills.qqbot_friendly.skill import is_qqbot_message, extract_qqbot_content

# 检测是否为QQ Bot消息
if is_qqbot_message(message):
    content = extract_qqbot_content(message)
    print(f"这是QQ Bot消息：{content}")
```