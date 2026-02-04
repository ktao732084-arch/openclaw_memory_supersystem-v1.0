# QQ Bot上下文 - 电脑本地配对架构信息

## 🏗️ 双实例架构配置

### 当前系统状态
- **服务器端**：OpenClaw（Gateway + Agent架构）
- **电脑本地**：Moltbot（技能系统架构）
- **网络状况**：电脑端OpenClaw下载受阻，仍用Moltbot

### 架构设计方案
```
服务器 (OpenClaw中枢)
  ├─ 主Agent (对外交互)
  ├─ 任务调度
  └─ 控制 → 电脑 Node

电脑 (Moltbot + Node)
  ├─ Node服务 (接受服务器调用)
  └─ 独立Agent (Moltbot，有自己的人格和记忆)
```

### 通信方案
由于两个系统协议不兼容，采用以下桥接方案：

#### 方案1：API网关桥接
```python
# 电脑端创建API服务
from flask import Flask, request

app = Flask(__name__)

@app.post('/to-openclaw')
def forward_to_openclaw():
    # 接收Moltbot消息，转换格式发给OpenClaw
    message = request.json['message']
    result = requests.post("服务器地址/api/sessions", json={"label": "server-bot", "message": message})
    return {"status": "success", "result": result.json()}
```

#### 方案2：文件同步模式
```yaml
电脑（Moltbot）
  ├─ 写消息到 ~/claw-sync/inbox.txt
  └─ 监听 ~/claw-sync/outbox.txt

服务器（OpenClaw）
  ├─ 监听 ~/claw-sync/inbox.txt
  └─ 写回复到 ~/claw-sync/outbox.txt
```

#### 方案3：SSH远程执行
```bash
# Moltbot通过SSH调用OpenClaw命令
subprocess.run(["ssh", "user@服务器", "openclaw sessions-send --label server-bot --message '你好'"])
```

## 🎯 优化的单网关方案

### 基于OpenClaw原生架构
```yaml
同一个Gateway
  ├─ Agent 1 (server-bot)     # 服务器端，处理外部交互
  ├─ Agent 2 (personal-assistant)  # 个人助手，专注本地任务
  └─ Sessions通信机制
```

### Sessions通信
```bash
# server-bot给personal-assistant发消息
sessions_send(label="personal-assistant", message="帮我整理今天的文档")

# personal-assistant回复
sessions_send(label="server-bot", message="已整理完成，共15个文件")
```

## 💡 最终实施方案

### 个人助手优化方案
```yaml
memory/
├── MEMORY.md           # 主记忆（偏好、习惯、重要事项）
├── daily/              # 每日日志
├── contacts.md         # 常联系人信息
└── knowledge/          # 个人知识库
    ├── work.md         
    ├── projects.md     
    └── ideas.md        

skills/
├── life-assistant/     # 生活助理（日程、提醒）
├── work-assistant/     # 工作助手（邮件、文档）
└── learning-partner/   # 学习伙伴（知识管理）

定时任务：
07:00 → 早安 + 今日待办
12:00 → 午间提醒
18:00 → 下班 + 今日总结
22:00 → 睡前检查
```

## 🔧 技术挑战与解决方案

### 网络问题
- **问题**：电脑端OpenClaw下载失败
- **解决方案**：继续用Moltbot，通过API桥接通信
- **状态**：待实施

### 异构系统整合
- **问题**：OpenClaw(Node.js) + Moltbot(架构差异)
- **解决方案**：API适配层 + 消息格式转换
- **状态**：方案已确定，等待实施

### 平台识别
- **问题**：无法准确识别QQ Bot消息
- **解决方案**：创建了专门的QQ Bot检测技能
- **状态**：✅ 已完成，正在使用

## 🚀 当前进展

### 已完成项目
- ✅ QQ Bot消息准确识别
- ✅ QQ Bot专用上下文管理
- ✅ 150K上下文容量优化
- ✅ 个人助手架构设计

### 待实施项目
- 🔄 服务器-电脑通信桥接
- 🔄 Moltbot-OpenClaw协议转换
- 🔄 个人助手技能开发
- 🔄 定时任务系统搭建

### 配置参数
```python
# QQ Bot上下文管理
qqbot_config = {
    'max_context_length': 110000,      # 最大上下文长度
    'compression_threshold': 80000,    # 开始压缩的阈值
    'new_session_threshold': 110000,    # 开新会话的阈值
    'max_history_messages': 200,       # 最大历史消息数
    'session_timeout': 60              # 会话超时时间
}
```

## 📋 下一步计划

1. **网络问题解决**：重新尝试OpenClaw下载
2. **通信桥接搭建**：实现Moltbot-OpenClaw通信
3. **个人助手开发**：实现核心技能功能
4. **定时任务实施**：建立提醒和任务管理

## 🎯 最终目标

实现一个完整的个人助手系统：
- 服务器端处理外部交互
- 本地端处理个人任务
- 两端通过智能通信协作
- QQ Bot作为统一交互界面