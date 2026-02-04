# 最简单的 TinyProxy 配置文件

# 把下面这些内容复制到 /etc/tinyproxy/tinyproxy.conf

Port 18789
Listen 0.0.0.0
Timeout 600
LogLevel Info
LogFile /var/log/tinyproxy/tinyproxy.log
MaxClients 100
Allow 81.70.79.133

---

## 手动配置步骤

### 1. 打开配置文件
```bash
sudo nano /etc/tinyproxy/tinyproxy.conf
```

### 2. 删除所有内容
在nano里：
- 按 `Ctrl + K` 删除行
- 或者按 `Ctrl + Shift + 6`，然后输入 `^$`，再按 `Ctrl + K`（删除到结尾）
- 或者按 `Alt + \` 然后 `ggVG`（vi里删除全部）

**或者更快：**
```bash
# 直接清空文件
echo "" | sudo tee /etc/tinyproxy/tinyproxy.conf
```

### 3. 粘贴上面的配置
把 `Port 18789` 开始那几行粘贴进去

### 4. 保存退出
nano: `Ctrl + X` → `Y` → `Enter`

### 5. 重启服务
```bash
sudo systemctl restart tinyproxy
sudo systemctl status tinyproxy
```

### 6. 检查是否成功
```bash
sudo netstat -tlnp | grep 18789
```

应该看到类似：
```
tcp    0    0    0.0.0.0:18789    0.0.0.0:*    LISTEN    12345/tinyproxy
```

### 7. 本地测试
```bash
curl -x http://127.0.0.1:18789 ifconfig.me
```

如果返回你的VPS IP，就成功了！

---

## 如果还是失败

### 查看错误日志
```bash
sudo tail -50 /var/log/tinyproxy/tinyproxy.log
```

### 查看系统日志
```bash
sudo journalctl -u tinyproxy -n 100
```

---

## 或者：用Python临时代理

如果tinyproxy一直有问题，用Python建个临时代理：

```bash
# 创建代理脚本
cat > /tmp/simple_proxy.py << 'PYEOF'
import socket
import select
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

class ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith(('http://', 'https://')):
            # 简单转发
            import urllib.request
            try:
                response = urllib.request.urlopen(self.path)
                content = response.read()
                self.send_response(200)
                self.send_header('Content-Type', response.headers.get('Content-Type', 'text/html'))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error(502, str(e))
        else:
            self.send_error(400, 'Bad Request')

    def do_CONNECT(self):
        self.send_error(405, 'Method Not Allowed')

def run_proxy(port=18789):
    server = HTTPServer(('0.0.0.0', port), ProxyHandler)
    print(f'Proxy running on port {port}')
    server.serve_forever()

if __name__ == '__main__':
    run_proxy()
PYEOF

# 运行
nohup python3 /tmp/simple_proxy.py > /tmp/proxy.log 2>&1 &

# 开放端口
sudo ufw allow 18789/tcp
```

这个Python代理很简单，但可能性能不高，测试用足够了。
