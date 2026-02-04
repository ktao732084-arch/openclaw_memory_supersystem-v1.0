# OpenClaw 代理配置 - 永久记忆

## 国内服务器代理访问外网配置

### 代理服务器信息
- **VPS IP**: 47.253.168.225
- **端口**: 18789
- **代理协议**: HTTP

### 配置方式

#### 1. 美国VPS端：TinyProxy
**配置文件位置**: `/etc/tinyproxy/tinyproxy.conf`

**关键配置**:
```conf
Port 18789
Listen 0.0.0.0
Timeout 600
LogLevel Info
LogFile "/var/log/tinyproxy/tinyproxy.log"  # 重要：LogFile必须用双引号！
MaxClients 100
Allow 81.70.79.133  # 国内服务器IP
```

**关键教训**：
- ❌ 错误：`LogFile /var/log/tinyproxy/tinyproxy.log`（无引号，导致语法错误）
- ✅ 正确：`LogFile "/var/log/tinyproxy/tinyproxy.log"`（必须加双引号）
- 验证方法：查看 `/usr/share/doc/tinyproxy/examples/tinyproxy.conf` 对比

**启动服务**:
```bash
sudo /usr/bin/tinyproxy -d -c /etc/tinyproxy/tinyproxy.conf
```

**验证运行**:
```bash
ps aux | grep tinyproxy
sudo ss -tlnp | grep 18789
```

---

#### 2. 国内服务器端：环境变量配置
**配置文件**: `~/.bashrc`

**添加内容**:
```bash
export HTTP_PROXY=http://47.253.168.225:18789
export HTTPS_PROXY=http://47.253.168.225:18789
```

**生效方式**:
```bash
# 已添加的终端自动加载
# 新开的终端需要手动加载
source ~/.bashrc
```

---

### 使用方法

#### 方法1：curl -x 参数（一次性使用）
```bash
curl -x http://47.253.168.225:18789 https://example.com
```

#### 方法2：环境变量（全局使用）
```bash
# 已通过~/.bashrc设置，source后自动生效
curl https://example.com  # 自动使用代理
```

#### 方法3：临时设置环境变量
```bash
HTTP_PROXY=http://47.253.168.225:18789 HTTPS_PROXY=http://47.253.168.225:18789 curl https://example.com
```

---

### 验证代理工作

```bash
# 测试代理是否返回VPS IP
curl -x http://47.253.168.225:18789 ifconfig.me
# 应返回：47.253.168.225

# 测试访问外网（Moltbook API）
curl -x http://47.253.168.225:18789 https://www.moltbook.com/api/v1/agents/status
```

---

### 故障排查

**如果代理无法连接**:
```bash
# 1. 检查VPS端tinyproxy进程
ps aux | grep tinyproxy

# 2. 检查端口监听
sudo ss -tlnp | grep 18789

# 3. 检查VPS防火墙
sudo ufw status | grep 18789

# 4. 查看日志
sudo tail -20 /var/log/tinyproxy/tinyproxy.log
```

**如果配置文件语法错误**:
- 检查LogFile是否加了双引号
- 对比默认配置：`cat /usr/share/doc/tinyproxy/examples/tinyproxy.conf`

---

### 相关记忆文件
- 详细配置记录：`memory/proxy-setup-2026-02-02.md`
- TinyProxy错误教训：`memory/2026-02-02.md`

---

**最后更新**: 2026-02-02
