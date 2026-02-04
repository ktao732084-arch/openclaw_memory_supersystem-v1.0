# SSH隧道配置修复

## 问题
SSH连接失败（status=255），需要先配置免密钥登录。

---

## 解决方案

### 步骤1：在国内服务器生成SSH密钥

```bash
# 生成RSA密钥
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""

# 查看公钥
cat ~/.ssh/id_rsa.pub
```

### 步骤2：把公钥添加到美国VPS

**把 `~/.ssh/id_rsa.pub` 的内容复制出来**，然后在美国VPS上执行：

```bash
# 添加公钥到authorized_keys
echo "YOUR_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys

# 设置权限
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

### 步骤3：修改systemd服务

在服务中添加密钥文件参数：

```bash
sudo tee /etc/systemd/system/ssh-tunnel.service << 'EOF'
[Unit]
Description=SSH SOCKS5 Tunnel
After=network.target

[Service]
User=root
ExecStart=/usr/bin/ssh -N -D 1080 -o ServerAliveInterval=60 -o ServerAliveCountMax=3 -i ~/.ssh/id_rsa root@47.253.168.225
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 重启服务
sudo systemctl daemon-reload
sudo systemctl start ssh-tunnel

# 查看状态
sudo systemctl status ssh-tunnel
```

**注意添加了 `-i ~/.ssh/id_rsa` 参数！**

---

## 快速方法（推荐）

如果觉得麻烦，可以用密码方式（不太安全但简单）：

```bash
# 创建使用密码的配置
sudo tee /etc/systemd/system/ssh-tunnel.service << 'EOF'
[Unit]
Description=SSH SOCKS5 Tunnel
After=network.target

[Service]
User=root
ExecStart=/usr/bin/ssh -N -D 1080 -o ServerAliveInterval=60 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=no root@47.253.168.225
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start ssh-tunnel
```

**注意：**
- `-o StrictHostKeyChecking=no` 不检查主机密钥（避免第一次连接时卡住）
- 需要在第一次连接时手动输入密码（SSH会弹出来）

---

## 验证

```bash
# 检查隧道是否运行
ps aux | grep "ssh -D 1080"

# 检查端口
sudo ss -tlnp | grep 1080
```

---

**先执行步骤1生成密钥，然后告诉我！**
