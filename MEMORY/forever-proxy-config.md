# 国内服务器代理访问外网 - 一劳永逸配置

## 方案A：SSH SOCKS5隧道（最像VPN）

### 优点
- ✅ 最像VPN体验
- ✅ 所有流量走隧道（HTTP、HTTPS、WebSocket、TCP）
- ✅ 不需要在美国VPS安装额外软件
- ✅ 简单稳定

### 缺点
- ⚠️ 需要保持SSH连接（断开=断网）
- ⚠️ 不像VPN那样后台稳定运行

---

### 配置步骤

#### 1. 在国内服务器配置SSH隧道（保持连接）

**方法1：手动启动SSH隧道**
```bash
# 前台运行SSH隧道（阻塞）
ssh -D 1080 root@47.253.168.225 -N

# 或者后台运行（用nohup）
nohup ssh -D 1080 root@47.253.168.225 -N > /dev/null 2>&1 &
```

**方法2：使用autossh自动重连（推荐）**

```bash
# 安装autossh
sudo apt install autossh -y

# 创建启动服务
sudo tee /etc/systemd/system/ssh-tunnel.service << 'EOF'
[Unit]
Description=SSH SOCKS5 Tunnel
After=network.target

[Service]
User=root
ExecStart=/usr/bin/ssh -N -D 1080 -o ServerAliveInterval=60 -o ServerAliveCountMax=3 root@47.253.168.225
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl daemon-reload
sudo systemctl start ssh-tunnel
sudo systemctl enable ssh-tunnel

# 查看状态
sudo systemctl status ssh-tunnel
```

**autossh的优势**：
- SSH断开自动重连
- 开机自动启动
- 后台稳定运行

---

#### 2. 配置所有工具使用SOCKS5代理

编辑 `~/.bashrc`：
```bash
echo 'export ALL_PROXY=socks5://127.0.0.1:1080' >> ~/.bashrc
echo 'export all_proxy=socks5://127.0.0.1:1080' >> ~/.bashrc

# 生效
source ~/.bashrc
```

---

#### 3. 使用方法

```bash
# 方法1：curl
curl --socks5 127.0.0.1:1080 https://twitter.com

# 方法2：环境变量（已设置后，自动使用）
curl https://twitter.com

# 方法3：临时指定
all_proxy=socks5://127.0.0.1:1080 curl https://twitter.com
```

---

## 方案B：TinyProxy（已配置）

### 现状
- ✅ 美国VPS上tinyproxy运行正常
- ✅ 端口18789已监听
- ✅ HTTP访问成功
- ⚠️ HTTPS连接有问题（Connection reset）

### 配置

已在 `~/.bashrc` 中配置：
```bash
export HTTP_PROXY=http://47.253.168.225:18789
export HTTPS_PROXY=http://47.253.168.225:18789
```

### 使用
```bash
curl -x http://47.253.168.225:18789 https://example.com
```

---

## 推荐使用方案

### 日常使用：方案A（SSH SOCKS5隧道）

**理由**：
- 最像VPN体验
- 所有协议都支持（HTTP、HTTPS、WebSocket等）
- 访问推特、Google等HTTPS网站稳定
- 一次配置，自动运行

### HTTP工具：方案B（TinyProxy）

**适用场景**：
- 只需要HTTP代理的工具
- git、npm、pip等命令行工具

---

## 切换使用

### 当前使用SSH隧道
```bash
# 检查SOCKS5隧道
ps aux | grep "ssh -D"

# 启动（如果没运行）
sudo systemctl start ssh-tunnel
```

### 当前使用TinyProxy
```bash
# 检查tinyproxy
ps aux | grep tinyproxy

# 使用
curl -x http://47.253.168.225:18789 https://example.com
```

---

## 完整配置示例

### 同时配置两种代理（备用）

在 `~/.bashrc` 中：
```bash
# TinyProxy（HTTP）
export HTTP_PROXY=http://47.253.168.225:18789
export HTTPS_PROXY=http://47.253.168.225:18789

# SSH SOCKS5隧道（所有协议）
export ALL_PROXY=socks5://127.0.0.1:1080
export all_proxy=socks5://127.0.0.1:1080
```

### 使用时选择

```bash
# 使用SOCKS5（像VPN）
curl --socks5 127.0.0.1:1080 https://twitter.com

# 使用TinyProxy（HTTP）
curl -x http://47.253.168.225:18789 https://example.com
```

---

## 推荐配置

**首选：SSH SOCKS5隧道 + autossh（方案A）**

因为：
- ✅ 最像VPN
- ✅ 支持所有协议
- ✅ 稳定运行（自动重连）
- ✅ 开机自启

---

**最后更新**: 2026-02-02
