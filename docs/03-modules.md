# 模块说明

## 模块结构

```
backend/app/
├── protocol/          # APDU/ASDU 编解码
│   ├── frame.py       # 帧编解码、粘包处理
│   └── messages.py    # 消息模型定义
├── robot/             # 机器人交互层
│   ├── basic_client.py  # TCP 客户端
│   ├── telemetry.py     # 遥测适配器
│   └── status.py        # 状态解析
├── navigation/        # 导航业务层
│   └── v010.py        # 导航报文构造
├── gimbal/            # 云台控制
│   ├── adapter.py     # 数尔云台适配器
│   └── handlers.py    # HTTP 处理器
├── video/             # 视频流
│   └── stream_manager.py  # RTSP 管理
├── auth/              # 认证
│   └── middleware.py  # 中间件
├── api/               # API 层
│   ├── router.py      # 路由分发
│   └── handlers.py    # 处理器
├── server.py          # 服务入口
└── config.py          # 配置管理
```

## protocol/ — 协议层

### frame.py — APDU 帧编解码

16 字节帧头，处理粘包/拆包。同步字 `EB 91 EB 90`，支持 JSON/XML 格式。

```python
# 帧头结构
| 同步 | 同步 | 同步 | 同步 | 长度 | 报文ID | 格式 | 预留 |
| 0xeb | 0x91 | 0xeb | 0x90 | 2B  | 2B    | 1B  | 7B  |
```

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

### basic_client.py — TCP 客户端

```python
client.connect(read_only=True)   # 状态订阅
client.send_control(msg)         # 控制命令（需门禁）
```

门禁条件：`control_enabled=True` + 三份证据（协议版本、固件版本、授权记录）

### telemetry.py — 遥测适配器

连接 AOS TCP 30001，接收状态消息。生产模式不发送心跳。

状态值：`REAL` / `SIMULATED` / `NO_DATA` / `STALE` / `ERROR`

### status.py — 状态解析

| Type | Command | 内容 |
|------|---------|------|
| 1002 | 3 | 异常列表 |
| 1002 | 4 | 运控状态（10Hz） |
| 1002 | 5 | 设备状态（电池、温度） |
| 1002 | 6 | 基础状态（运动、充电） |
| 1007 | 1 | 导航任务状态 |
| 1007 | 2 | 位姿信息 |
| 1007 | 3 | 导航异常（≥V1.1.8） |
| 2002 | 1 | 感知状态 |

## navigation/ — 导航业务层

```python
from backend.app.navigation.v010 import SinglePointNavigation

nav = SinglePointNavigation(
    map_id=1,
    pos_x=0.5,
    pos_y=0.3,
    angle_yaw=0.0,
    gait=GAIT_FLAT_AGGRESSIVE  # 0x3002
)
msg = nav.to_message(safety_snapshot)  # → PatrolMessage (Type=1003, Cmd=1)
```

步态常量：
- `GAIT_FLAT_AGGRESSIVE = 0x3002`（平地敏捷）
- `GAIT_FLAT_STANDARD = 0x1001`（平地标准）

## gimbal/ — 云台控制

数尔安防 SR-UPA810T609 热成像云台适配。

协议：WEB 2.0（Merlin）

连接优先级：
1. 配置的 `gimbal_host`
2. 默认 IP `192.168.1.108`
3. 网络扫描（仅 M20 网段）

API 端点：
| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/gimbal/scan` | GET | 扫描并连接云台 |
| `/api/v1/gimbal/state` | GET | 获取云台状态 |
| `/api/v1/gimbal/move` | POST | 方向控制 |
| `/api/v1/gimbal/zoom` | GET | 变倍控制 |
| `/api/v1/gimbal/angle` | POST | 角度设置 |
| `/api/v1/gimbal/device/info` | GET | 设备信息 |
| `/api/v1/gimbal/video` | GET | 视频流地址 |

## video/ — 视频流

RTSP 地址（候选值，待实测）：
- 前相机：`rtsp://10.21.31.103:8554/video1`
- 后相机：`rtsp://10.21.31.103:8554/video2`
- 云台可见光：`rtsp://192.168.1.108:554/id=1&type=0`
- 云台热成像：`rtsp://192.168.1.108:554/id=2&type=0`

需现场确认：编码格式、分辨率、帧率。

## 测试覆盖

| 代码模块 | 测试文件 |
|----------|----------|
| `protocol/frame.py` | `test_frame.py` |
| `protocol/messages.py` | `test_messages.py` |
| `robot/status.py` | `test_status.py` |
| `robot/basic_client.py` | `test_basic_client.py` |
| `robot/telemetry.py` | `test_telemetry.py` |
| `navigation/v010.py` | `test_navigation_v010.py` |
| `gimbal/adapter.py` | `test_gimbal_adapter.py` |
