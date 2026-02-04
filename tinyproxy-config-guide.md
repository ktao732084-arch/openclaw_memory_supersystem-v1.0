# TinyProxy 配置指南

## 安装

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install tinyproxy
```

### CentOS/RHEL
```bash
sudo yum install epel-release
sudo yum install tinyproxy
```

---

## 基础配置

编辑配置文件：
```bash
sudo nano /etc/tinyproxy/tinyproxy.conf
```

### 核心配置项

#### 1. 监听端口
```conf
Port 8888
```
默认8888，可以改成你想要的端口（如8080、3128）

#### 2. 监听地址
```conf
# 只监听本地（安全）
Listen 127.0.0.1

# 监听所有网卡（允许外网访问）
# Listen 0.0.0.0
```

#### 3. 允许访问的IP白名单（重要！）
```conf
# 只允许本机访问
Allow 127.0.0.1

# 允许特定IP访问（比如你的本地IP）
# Allow 1.2.3.4

# 允许整个网段（危险）
# Allow 192.168.1.0/24

# 允许所有IP（非常危险！）
# Allow 0.0.0.0/0
```

#### 4. 禁用日志（可选）
```conf
LogLevel Info
LogFile /var/log/tinyproxy/tinyproxy.log
# 或者关闭日志：
# Syslog Off
```

#### 5. 最大连接数
```conf
MaxClients 100
```

---

## 完整示例配置（只允许本地）

```conf
Port 8888
Listen 127.0.0.1
Timeout 600
DefaultErrorFile "/usr/share/tinyproxy/default.html"
StatFile "/usr/share/tinyproxy/stats.html"
Logfile "/var/log/tinyproxy.log"
LogLevel Info
MaxClients 100
MinSpareServers 5
MaxSpareServers 20
StartServers 10
MaxRequestsPerChild 0

# 只允许本机访问
Allow 127.0.0.1
```

---

## 允许外网访问（你需要这个）

如果你想在本地机器使用VPS上的代理：

```conf
Port 8888
Listen 0.0.0.0
Timeout 600
LogLevel Info
MaxClients 100

# 允许你的IP（替换成你的真实IP）
Allow YOUR_PUBLIC_IP
# 或者允许IP段
# Allow YOUR_PUBLIC_IP/24
```

**如何找到你的公网IP：**
```bash
curl ifconfig.me
```

---

## 启动/重启

```bash
# 启动
sudo systemctl start tinyproxy

# 停止
sudo systemctl stop tinyproxy

# 重启
sudo systemctl restart tinyproxy

# 开机自启
sudo systemctl enable tinyproxy
```

---

## 防火墙配置

### Ubuntu/Debian (UFW)
```bash
# 开放端口
sudo ufw allow 8888/tcp

# 查看状态
sudo ufw status
```

### CentOS/RHEL (firewalld)
```bash
# 开放端口
sudo firewall-cmd --permanent --add-port=8888/tcp
sudo firewall-cmd --reload

# 查看状态
sudo firewall-cmd --list-all
```

---

## 本地使用代理

### curl
```bash
curl -x http://YOUR_VPS_IP:8888 https://example.com
```

### 环境变量
```bash
export http_proxy=http://YOUR_VPS_IP:8888
export https_proxy=http://YOUR_VPS_IP:8888
```

### 配置软件（git/npm/pip等）

#### Git
```bash
git config --global http.proxy http://YOUR_VPS_IP:8888
git config --global https.proxy http://YOUR_VPS_IP:8888
```

#### npm
```bash
npm config set proxy http://YOUR_VPS_IP:8888
npm config set https-proxy http://YOUR_VPS_IP:8888
```

---

## 安全建议

1. **不要使用 `Allow 0.0.0.0/0`** - 这会让所有人都能用你的代理
2. **使用白名单** - 只允许你自己的IP访问
3. **定期检查日志** - `tail -f /var/log/tinyproxy/tinyproxy.log`
4. **考虑认证** - tinyproxy不支持密码认证，如果需要可以用 Squid 或 Nginx 反向代理
5. **监控流量** - 防止被滥用导致流量超限

---

## 验证代理是否工作

```bash
# 查看代理返回的IP（应该是你的VPS IP）
curl -x http://YOUR_VPS_IP:8888 ifconfig.me
```

如果返回VPS的IP，说明代理正常工作。

---

**需要我帮你写一个针对你具体需求的配置文件吗？告诉我：**
1. 端口号（默认8888还是别的？）
2. 你的本地IP（用于白名单）
3. 主要用途（npm加速？git代理？还是翻墙？）
