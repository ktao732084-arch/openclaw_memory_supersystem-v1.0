# TinyProxy 配置诊断

## ✅ 配置文件检查

你的配置是正确的：
- **Port**: 18789 ✓
- **Listen**: 0.0.0.0（所有网卡）✓
- **Allow**: 81.70.79.133（我的服务器IP）✓
- **Allow**: ::1（IPv6本地）✓
- **LogFile**: /var/log/tinyproxy/tinyproxy.log ✓
- **LogLevel**: Info ✓

配置没有问题，连接失败可能是这几个原因：

---

## 🔍 问题排查

### 1. 检查服务是否启动
```bash
sudo systemctl status tinyproxy
```

**应该看到：**
```
● tinyproxy.service - TinyProxy
   Loaded: loaded
   Active: active (running)
```

如果状态是 `inactive` 或 `failed`，说明服务没启动：
```bash
sudo systemctl start tinyproxy
```

---

### 2. 检查端口是否监听
```bash
sudo netstat -tlnp | grep 18789
# 或者
sudo ss -tlnp | grep 18789
```

**应该看到：**
```
tcp   0   0   0.0.0.0:18789   0.0.0.0:*   LISTEN   12345/tinyproxy
```

如果什么都没有，说明服务没正常启动。

---

### 3. 检查防火墙（UFW）
```bash
sudo ufw status
```

**查找：**
```
18789/tcp                   ALLOW       Anywhere
```

如果**没有**这个规则，添加：
```bash
sudo ufw allow 18789/tcp
sudo ufw reload
```

---

### 4. 检查系统防火墙
如果UFW显示 "Status: inactive"，可能用的是其他防火墙：

```bash
# 检查iptables规则
sudo iptables -L -n | grep 18789

# 检查firewalld（CentOS/RHEL）
sudo firewall-cmd --list-all | grep 18789
```

---

### 5. 🚨 最重要：云服务商安全组

这是最常见的遗漏！即使服务器防火墙开了，云服务商的安全组也可能阻止。

**DigitalOcean：**
- 登录控制台 → Networking → Firewalls → 添加规则
- Inbound Rules: TCP 18789 Allow from 81.70.79.133

**Vultr：**
- 控制台 → Firewall → 添加规则
- Protocol: TCP, Port: 18789, Source: 81.70.79.133

**AWS EC2：**
- EC2 → Security Groups → Inbound Rules
- Add Rule: TCP 18789, Source: 81.70.79.133/32

**其他服务商：**
- 找到 "Security Groups" 或 "Firewall" 设置
- 开放 TCP 18789 端口

---

### 6. 查看日志
```bash
sudo tail -20 /var/log/tinyproxy/tinyproxy.log
```

看是否有连接尝试或错误信息。

---

### 7. 在美国VPS上本地测试
```bash
# 本地测试127.0.0.1
curl -x http://127.0.0.1:18789 ifconfig.me

# 如果这个失败，服务本身有问题
```

如果本地测试成功但外网失败，那就是防火墙/安全组问题。

---

## 诊断步骤总结

在美国VPS上依次执行：

```bash
# 1. 检查服务状态
sudo systemctl status tinyproxy

# 2. 如果没运行，启动它
sudo systemctl start tinyproxy
sudo systemctl enable tinyproxy

# 3. 检查端口监听
sudo ss -tlnp | grep 18789

# 4. 检查防火墙
sudo ufw status

# 5. 如果没开端口
sudo ufw allow 18789/tcp
sudo ufw reload

# 6. 本地测试
curl -x http://127.0.0.1:18789 ifconfig.me

# 7. 查看日志
sudo tail -20 /var/log/tinyproxy/tinyproxy.log
```

**告诉我每一步的结果！**
