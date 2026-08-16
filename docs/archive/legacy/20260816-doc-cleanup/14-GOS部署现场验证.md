# GOS部署现场验证手册

## 1. 验证前准备

### 1.1 系统要求
- GOS: Ubuntu 20.04.6 LTS (aarch64)
- Python: 3.8.10+（系统预装）
- FFmpeg: 7.1+（离线安装包）
- 网络: 10.21.31.0/24

### 1.2 网络要求
GOS需访问：

| 目标 | 地址 | 端口 | 协议 | 用途 |
|------|------|------|------|------|
| AOS | 10.21.31.103 | 30001 | TCP | basic_server |
| AOS | 10.21.31.103 | 30000 | UDP | basic_server |
| AOS | 10.21.31.103 | 8554 | RTSP | 视频流 |
| 云台 | 10.21.31.108 | 80 | HTTP | 云台控制 |
| 云台 | 10.21.31.108 | 554 | RTSP | 热成像视频 |

## 2. 部署后验证流程

### 2.1 服务健康检查

```bash
# 登录GOS
ssh user@10.21.31.104

# 检查服务状态
systemctl --user status m20-patrol-readonly

# 查看服务日志
journalctl --user -u m20-patrol-readonly -n 50 --no-pager
```

**期望输出**:
```
● m20-patrol-readonly.service - M20 Patrol Robot Read-Only Service
   Loaded: loaded (/home/user/.config/systemd/user/m20-patrol-readonly.service)
   Active: active (running)
 Main PID: 12345 (python3)
    Tasks: 5 (limit: 4915)
   CGroup: /user.slice/user-1000.slice/user@1000.service/m20-patrol-readonly.service
```

### 2.2 API健康检查

```bash
# 健康端点
curl -s http://localhost:8080/api/v1/health | python3 -m json.tool

# 期望输出
{
  "service": "m20-patrol-web",
  "runtime_mode": "realtime",
  "read_only_mode": false,
  "control_enabled": true,
  "source": "REAL",
  "connected": true,
  "tcp_connected": true,
  "valid_frames": 1234,
  "bytes_received": 5678,
  "last_message_type": 1002,
  "received_at": "2026-08-16T12:00:00+08:00",
  "age_ms": 50
}
```

### 2.3 状态数据查询

```bash
# 获取最新状态
curl -s http://localhost:8080/api/v1/status/latest | python3 -m json.tool

# 期望关键字段
{
  "source": "REAL",
  "connected": true,
  "data": {
    "basic": {
      "motion_state": 1,
      "gait": 12290,
      "charge": 95,
      "hes": 0
    },
    "motion": {
      "roll": 0.0,
      "pitch": 0.0,
      "yaw": 0.0,
      "linear_x": 0.0,
      "linear_y": 0.0
    },
    "device": {
      "battery_list": [
        {"BatteryLevel": 95, "Voltage": 25.5, "serial": "B001"},
        {"BatteryLevel": 92, "Voltage": 25.2, "serial": "B002"}
      ]
    },
    "nav_status": {
      "status": 0,
      "loop_count": 0
    }
  },
  "battery_percent": 95,
  "received_at": "2026-08-16T12:00:00+08:00"
}
```

### 2.4 TCP连接验证

```bash
# 测试TCP连接（超时5秒）
timeout 5 bash -c 'echo | nc -v 10.21.31.103 30001'

# 期望输出
# Ncat: Version 7.80 ( https://nmap.org/ncat )
# Ncat: Connected to 10.21.31.103:30001.
```

### 2.5 导航状态检查

```bash
# 导航状态
curl -s http://localhost:8080/api/v1/navigation/status | python3 -m json.tool

# 期望输出
{
  "authorized": true,
  "authorized_by": "dev",
  "authorized_at": "2026-08-16T11:00:00+00:00",
  "status": 0,
  "control_enabled": true
}
```

## 3. 常见问题排查

### 3.1 NO_DATA 问题

**症状**: UI显示"NO DATA / WAITING"

**排查步骤**:
```bash
# 1. 检查TCP端口连通性
timeout 5 bash -c 'echo | nc -v 10.21.31.103 30001'
# 期望: Connected to 10.21.31.103:30001

# 2. 检查AOS IP是否正确
ping -c 3 10.21.31.103

# 3. 查看服务日志
journalctl --user -u m20-patrol-readonly -n 100 --no-pager -l
```

**可能原因**:
- TCP 30001端口不通（通信网络问题）
- AOS主机地址变更
- 服务未启动

### 3.2 心跳问题

**症状**: 连接成功但数据过时

**排查命令**:
```bash
# 检查心跳发送
curl -s http://localhost:8080/api/v1/status/latest | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'age_ms={d.get(\"age_ms\")}')"

# 期望值: age_ms < 3000ms
```

### 3.3 授权问题

**症状**: 控制指令返回403

**排查**:
```bash
# 检查当前模式
curl -s http://localhost:8080/api/v1/health | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'read_only_mode={d.get(\"read_only_mode\")}, control_enabled={d.get(\"control_enabled\")}')"

# 修改manifest
vim ~/m20-patrol-robot/deploy/readonly-manifest.json
# 设置: "control_enabled": true, "read_only_mode": false
```

## 4. 验证清单

部署完成后，逐项检查：

- [ ] 服务运行中: `systemctl --user status m20-patrol-readonly`
- [ ] 健康检查通过: `curl http://localhost:8080/api/v1/health`
- [ ] TCP连接正常: `nc -zv 10.21.31.103 30001`
- [ ] 状态数据更新: `curl http://localhost:8080/api/v1/status/latest`
- [ ] UI可访问: 浏览器打开 `http://10.21.31.104:8080`
- [ ] 云台连接: 检查Web界面云台面板

## 5. 回滚方案

如部署后问题严重，执行回滚：

```bash
# 停止服务
systemctl --user stop m20-patrol-readonly

# 删除当前版本
rm -rf ~/m20-patrol-robot/current

# 解压旧版本
unzip -q ~/m20-patrol-robot.zip -d ~/m20-patrol-robot/backup

# 从备份恢复
cp -r ~/m20-patrol-robot/backup/* ~/m20-patrol-robot/current/

# 重启服务
systemctl --user start m20-patrol-readonly
```
