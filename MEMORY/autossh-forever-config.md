# 真正一劳永逸的代理方案

## 推荐方案：autossh + SSH密钥

### 为什么这个方案最好？

1. **自动重连** - SSH断了自动连上，不用管
2. **开机自启** - 配置systemd服务，开机自动运行
3. **无密码** - SSH密钥方式，不用每次输入密码
4. **稳定可靠** - autossh专门设计用于保持SSH隧道
5. **支持所有协议** - HTTP、HTTPS、WebSocket等

---

## 配置步骤（两边操作）

### 步骤1：国内服务器端

#### 1.1 生成SSH密钥对
```bash
# 生成密钥
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_tunnel -N ""

# 查看私钥和公钥
ls -la ~/.ssh/id_rsa_tunnel*
```

#### 1.2 查看公钥
```bash
cat ~/.ssh/id_rsa_tunnel.pub
```

**把这行复制出来！**

---

### 步骤2：美国VPS端

#### 2.1 登录美国VPS
```bash
# SSH登录到美国VPS
ssh root@47.253.168.225
```

#### 2.2 安装autossh
```bash
# 安装autossh
sudo apt update
sudo apt install autossh -y

# 验证安装
which autossh
```

#### 2.3 添加国内服务器的公钥到美国VPS
```bash
# 在美国VPS上执行（把上面复制的公钥粘贴到下面）
echo "YOUR_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys

# 验证添加成功
cat ~/.ssh/authorized_keys | tail -3

# 设置权限
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

#### 2.4 创建autossh服务文件
```bash
# 在美国VPS上创建
sudo tee /etc/systemd/system/autossh-tunnel.service << 'EOF'
[Unit]
Description=AutoSSH SOCKS5 Tunnel to China Server
After=network.target

[Service]
User=root
ExecStart=/usr/bin/autossh -M 0 -N -D 1080 -o "ServerAliveInterval 60" -o "ServerAliveCountMax 3" -o "ExitOnForwardFailure yes" -o "ConnectTimeout 10" CHINA_SERVER_IP

[Install]
WantedBy=multi-user.target
EOF
```

**重要**：把 `CHINA_SERVER_IP` 改成国内服务器IP `81.70.79.133`！

#### 2.5 启动并设为开机自启
```bash
# 启动服务
sudo systemctl daemon-reload
sudo systemctl start autossh-tunnel
sudo systemctl enable autossh-tunnel

# 查看状态
sudo systemctl status autossh-tunnel
```

---

### 步骤3：国内服务器配置使用

#### 3.1 在国内服务器上配置autossh反向隧道
```bash
# 在国内服务器上创建
sudo tee /etc/systemd/system/autossh-reverse.service << 'EOF'
[Unit]
Description=AutoSSH Reverse Tunnel
After=network.target

[Service]
ExecStart=/usr/bin/autossh -M 0 -N -R 1080:127.0.0.1:1080 -o "ServerAliveInterval 60" -o "ServerAliveCountMax 3" -o "ExitOnForwardFailure yes" -o "ConnectTimeout 10" root@47.253.168.225 -i ~/.ssh/id_rsa_tunnel

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl daemon-reload
sudo systemctl start autossh-reverse
sudo systemctl enable autossh-reverse

# 查看状态
sudo systemctl status autossh-reverse
```

#### 3.2 配置全局使用SOCKS5代理
```bash
# 编辑~/.bashrc，添加SOCKS5配置
echo 'export ALL_PROXY=socks5://127.0.0.1:1080' >> ~/.bashrc
echo 'export all_proxy=socks5://127.0.0.1:1080' >> ~/.bashrc

# 生效
source ~/.bashrc

# 验证
echo $ALL_PROXY
```

---

## 最终效果

### 配置完成后的使用

#### 查看状态
```bash
# 在国内服务器上查看
sudo systemctl status autossh-reverse

# 在美国VPS上查看
sudo systemctl status autossh-tunnel
```

#### 测试代理
```bash
# 通过SOCKS5代理访问外网
curl --socks5 127.0.0.1:1080 https://twitter.com
curl --socks5 127.0.0.1:1080 https://www.google.com

# 或者用环境变量（已设置）
curl https://twitter.com
curl https://www.google.com
```

---

## 为什么这个方案"一劳永逸"？

### ✅ 自动重连
- autossh会监控SSH连接
- 断了自动重连
- 不需要手动干预

### ✅ 开机自启
- systemd服务管理
- 开机自动启动
- 断了自动重启

### ✅ 无密码
- SSH密钥认证
- 不用每次输入密码
- 更安全更方便

### ✅ 支持所有协议
- SOCKS5支持HTTP、HTTPS、WebSocket
- 不像tinyproxy那样对HTTPS有问题

### ✅ 双向保障
- 美国VPS用autossh主动连接国内服务器
- 国内服务器用autossh主动连接美国VPS
- 任一边断都能自动重连

---

## 快速总结

### 国内服务器端
1. 生成SSH密钥：`ssh-keygen -t rsa -f ~/.ssh/id_rsa_tunnel`
2. 查看公钥：`cat ~/.ssh/id_rsa_tunnel.pub`
3. 创建autossh服务（systemd配置好）
4. 启动服务：`sudo systemctl start autossh-reverse`
5. 配置环境变量：`export ALL_PROXY=socks5://127.0.0.1:1080`

### 美国VPS端
1. 安装autossh：`sudo apt install autossh -y`
2. 添加国内服务器公钥到 `~/.ssh/authorized_keys`
3. 创建autossh服务（systemd配置好）
4. 启动服务：`sudo systemctl start autossh-tunnel`

### 使用
```bash
# 任何网络请求都走代理
curl https://twitter.com
curl https://www.google.com
git clone https://github.com/xxx
npm install xxx
```

---

**配置完成后，以后再也不用手动启动SSH了！断了自动重，开机自动连。**

需要我帮你生成SSH密钥吗？
