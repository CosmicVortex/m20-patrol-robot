# GOS连接诊断指南

**问题**: 部署在GOS后，Web界面显示"NO DATA / WAITING"，所有数据为空

**原因分析**: 需要确认GOS到AOS的TCP 30001端口连接是否正常

---

## 快速诊断步骤

### 步骤1：在GOS上执行诊断脚本

```bash
# SSH登录到GOS
ssh user@10.21.31.104

# 执行诊断脚本
bash deploy/scripts/diagnose_gos_connection.sh
```

### 步骤2：检查关键输出

**成功的标志**:
```
✅ TCP 30001 连接成功
basic_server状态: active (running)
```

**失败的标志**:
```
❌ TCP 30001 连接失败: Connection refused
或
❌ TCP 30001 连接失败: Network is unreachable
```

---

## 常见问题排查

### 问题1: AOS主机不可达

**症状**: ping失败，TCP连接超时

**解决**:
```bash
# 在GOS上检查网络
ip addr show
route -n

# 确认AOS和GOS在同一网段
ping 10.21.31.103

# 如果不在同一网段，检查路由器/交换机配置
```

### 问题2: basic_server未运行

**症状**: TCP连接被拒绝 (Connection refused)

**解决**:
```bash
# SSH登录到AOS
ssh root@10.21.31.103

# 检查服务状态
systemctl status basic_server

# 如果未运行，启动服务
systemctl start basic_server

# 设置开机自启
systemctl enable basic_server
```

### 问题3: 防火墙阻止连接

**症状**: TCP连接超时 (无响应)

**解决**:
```bash
# 在AOS上检查防火墙
iptables -L -n | grep 30001

# 添加规则允许TCP 30001
iptables -A INPUT -p tcp --dport 30001 -j ACCEPT

# 保存规则
iptables-save > /etc/iptables/rules.v4
```

### 问题4: Python服务未正确启动

**症状**: Web界面可访问，但显示"NO DATA"

**解决**:
```bash
# 检查服务日志
journalctl -u m20-patrol-readonly.service -n 50 --no-pager

# 重启服务
systemctl restart m20-patrol-readonly.service

# 检查端口监听
ss -tlnp | grep 8080
```

---

## 预期连接流程

```
GOS (10.21.31.104)
    |
    | TCP 30001
    v
AOS basic_server (10.21.31.103)
    |
    | Type=1002 Cmd=6 (BasicStatus, 2Hz)
    | Type=1002 Cmd=4 (MotionStatus, 10Hz)
    | Type=1002 Cmd=5 (DeviceStatus, 2Hz)
    v
Web API /api/v1/status
    |
    v
前端显示
```

---

## 调试模式

### 查看详细日志

```bash
# 启用调试日志
export M20_LOG_LEVEL=DEBUG

# 重启服务
systemctl restart m20-patrol-readonly.service

# 查看实时日志
journalctl -u m20-patrol-readonly.service -f
```

### 手动测试连接

```python
# 在GOS上执行
python3 -c "
import socket
import json
from datetime import datetime

host = '10.21.31.103'
port = 30001

try:
    sock = socket.create_connection((host, port), timeout=3)
    print(f'✅ TCP连接成功: {host}:{port}')
    
    # 发送位置查询
    header = bytes([0xeb, 0x91, 0xeb, 0x90])
    asdu = json.dumps({
        'PatrolDevice': {
            'Type': 1007,
            'Command': 2,
            'Time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Items': {}
        }
    }).encode('utf-8')
    length = len(asdu).to_bytes(2, 'little')
    msg_id = (1).to_bytes(2, 'little')
    fmt = bytes([0x01])  # JSON
    reserved = bytes(7)
    apdu = header + length + msg_id + fmt + reserved + asdu
    
    sock.sendall(apdu)
    print(f'📤 已发送位置查询 ({len(apdu)} bytes)')
    
    # 尝试接收
    sock.settimeout(2)
    try:
        data = sock.recv(4096)
        print(f'📥 收到响应 ({len(data)} bytes)')
    except socket.timeout:
        print('⏱️ 无响应 (正常，订阅模式可能需要先发送订阅请求)')
    
    sock.close()
    
except Exception as e:
    print(f'❌ 连接失败: {type(e).__name__}: {e}')
"
```

---

## 状态码说明

| source | connected | 含义 |
|--------|-----------|------|
| REAL | true | ✅ 正常连接，有真实数据 |
| REAL | false | ⚠️ 之前连接过，现在断开 |
| NO_DATA | false | ℹ️ 等待连接 |
| STALE | false | ⚠️ 数据过时 (3秒无更新) |
| ERROR | false | ❌ 通信异常 |

---

## 联系支持

如果以上步骤无法解决问题，请提供以下信息：

1. 诊断脚本输出
2. `journalctl -u m20-patrol-readonly.service -n 100` 日志
3. `ping 10.21.31.103` 结果
4. `nc -zv 10.21.31.103 30001` 结果
