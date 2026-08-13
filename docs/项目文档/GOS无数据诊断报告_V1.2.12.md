# GOS无数据诊断报告 V1.2.12

**日期**: 2026-08-14  
**问题**: Web界面显示"NO DATA / WAITING"，所有数据为空

---

## 根本原因分析

### 代码实现检查

✅ **已实现的功能**:
1. `telemetry.py` - TCP 30001连接逻辑正确
2. `basic_client.py` - basic_server协议解析正确
3. `status.py` - 消息解析器支持Type=1002所有命令
4. `server.py` - Web服务启动逻辑正确
5. `manifest.json` - 配置正确指向AOS (10.21.31.103:30001)

### 无数据的可能原因

| 原因 | 概率 | 检查方法 |
|------|------|----------|
| AOS主机未开机 | 高 | `ping 10.21.31.103` |
| basic_server未运行 | 高 | `systemctl status basic_server` |
| 防火墙阻止TCP 30001 | 中 | `nc -zv 10.21.31.103 30001` |
| 网络不通 (不同网段) | 中 | `ip addr show` |
| Python服务启动失败 | 低 | `journalctl -u m20-patrol-readonly` |

---

## 立即执行步骤

### 步骤1：在GOS上运行诊断

```bash
# SSH登录到GOS
ssh user@10.21.31.104

# 运行诊断脚本
bash deploy/scripts/diagnose_gos_connection.sh
```

### 步骤2：检查关键输出

**期望看到**:
```
✅ TCP 30001 连接成功
basic_server状态: active (running)
```

**如果看到失败**:
```
❌ TCP 30001 连接失败: Connection refused
```
→ basic_server未运行，需要在AOS上启动

---

## 常见故障排查

### 故障1: AOS主机不可达

```bash
# 在GOS上
ping 10.21.31.103

# 如果ping失败，检查网络
ip addr show
# 确认GOS有10.21.31.x的IP地址
```

### 故障2: basic_server未运行

```bash
# SSH登录AOS
ssh root@10.21.31.103

# 检查状态
systemctl status basic_server

# 启动服务
systemctl start basic_server

# 设置开机自启
systemctl enable basic_server
```

### 故障3: 防火墙阻止

```bash
# 在AOS上
iptables -L -n | grep 30001
iptables -A INPUT -p tcp --dport 30001 -j ACCEPT
iptables-save > /etc/iptables/rules.v4
```

---

## 连接流程图

```
┌─────────────────────────────────────────────────────────────┐
│ GOS (10.21.31.104)                                         │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Python Web Server (:8080)                               │ │
│ │   └─ TelemetryAdapter._run_loop()                       │ │
│ │       └─ BasicServerClient.connect(10.21.31.103:30001) │ │
│ │           └─ TCP Socket → basic_server                  │ │
│ └─────────────────────────────────────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │ TCP 30001
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ AOS (10.21.31.103)                                         │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ basic_server (TCP 30001)                                │ │
│ │   ├─ Type=1002 Cmd=6 → BasicStatus (2Hz)               │ │
│ │   ├─ Type=1002 Cmd=4 → MotionStatus (10Hz)             │ │
│ │   ├─ Type=1002 Cmd=5 → DeviceStatus (2Hz)              │ │
│ │   └─ Type=1007 Cmd=2 → Position (on query)            │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 预期数据流

当连接成功后，你应该看到：

```json
{
  "source": "REAL",
  "connected": true,
  "battery": 95,
  "battery_left": 95,
  "battery_right": 92,
  "motion_state": 0,
  "position": {"pos_x": 0.0, "pos_y": 0.0},
  "nav_status": {"loop_count": 0}
}
```

---

## 文档更新

已添加以下诊断工具：
- `docs/项目文档/diagnose_connection.py` - Python诊断脚本
- `deploy/scripts/diagnose_gos_connection.sh` - Bash诊断脚本
- `docs/项目文档/GOS连接诊断指南.md` - 详细排查指南

---

**下一步**: 请在GOS上运行诊断脚本，并将输出结果发给我分析。
