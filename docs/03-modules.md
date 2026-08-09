# 03 — 模块说明

## 模块总览

```
backend/app/
├── protocol/          # APDU/ASDU 编解码
├── robot/             # TCP客户端、状态解析、遥测
├── navigation/        # 导航报文构造、安全门控
├── video/             # RTSP管理、视频流
└── dashboard_realtime.py  # 唯一入口（连接AOS，返回实时状态）
```

## protocol/ — 协议层

### frame.py — APDU帧编解码

16字节帧头，处理粘包/拆包。同步字 `EB 91 EB 90`，支持JSON/XML格式。

### messages.py — 消息模型

```python
PatrolMessage(
    message_type: int,    # 100, 1002, 1003, 1004, 1007, 2002
    command: int,
    sent_at: str,
    items: dict,
    message_id: int,      # 请求/响应关联
)
```

## robot/ — 机器人交互层

### basic_client.py — TCP客户端

```python
client.connect(read_only=True)   # 状态订阅
client.send_control(msg)         # 控制命令（需门禁）
```

门禁：`control_enabled=True` + 三份证据（协议、固件、权限）

### telemetry.py — 遥测适配器

连接 AOS TCP 30001，接收状态消息。生产模式不发送心跳。

状态值：`REAL` / `SIMULATED` / `NO_DATA` / `STALE` / `ERROR`

### status.py — 状态解析

| Type | Command | 内容 |
|------|---------|------|
| 1002 | 3 | 异常列表 |
| 1002 | 4 | 运控状态 |
| 1002 | 5 | 设备状态 |
| 1002 | 6 | 基础状态 |
| 1007 | 1,2,3 | 导航状态/位置/异常 |
| 2002 | 1 | 感知状态 |

## navigation/ — 导航业务层

```python
from navigation.v010 import SinglePointNavigation

nav = SinglePointNavigation(map_id=1, pos_x=0.5, pos_y=0.3, angle_yaw=0.0)
msg = nav.to_message(safety_snapshot)  # → PatrolMessage (1003/1)
```

步态常量：`GAIT_FLAT_AGGRESSIVE=0x3002`，`GAIT_FLAT_STANDARD=0x1001`

## video/ — 视频流

RTSP地址（候选）：
- 前：`rtsp://10.21.31.103:8554/video1`
- 后：`rtsp://10.21.31.103:8554/video2`

需现场确认可达性、鉴权、编码格式。

## dashboard_realtime.py — 入口

绑定 `10.21.31.104:8080`，提供状态API和视频接口。

```bash
bash deploy/scripts/deploy-readonly.sh --one-shot
```

## 测试覆盖

| 代码 | 测试 |
|------|------|
| protocol/frame.py | test_frame.py |
| protocol/messages.py | test_messages.py |
| robot/status.py | test_status.py |
| robot/basic_client.py | test_basic_client.py |
| navigation/v010.py | test_navigation_v010.py |
| dashboard_realtime.py | test_dashboard.py |
