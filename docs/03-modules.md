# 03 — 模块说明

## 模块总览

```
backend/app/
├── protocol/          # 协议层：APDU帧编解码
├── robot/             # 机器人交互层：TCP客户端、状态解析
├── navigation/        # 导航业务层：报文构造、安全门控
├── video/             # 视频流管理层：RTSP管理、WebSocket
└── dashboard_realtime.py # 唯一实时仪表盘入口
```

## protocol/ — 协议层

### frame.py — APDU 帧编解码

**职责**：实现 V1.2.1 §1.1.5 定义的16字节 APDU 帧编解码和增量解帧。

**核心能力**：
- 编码：`header(16字节) + payload(ASDU)` → 字节流
- 解码：字节流 → 帧列表（处理粘包、拆包、截断）
- 校验：同步字 `EB 91 EB 90`、长度范围、格式位、保留字节

**关键常量**：
```python
SYNC_WORD = b"\xeb\x91\xeb\x90"   # 同步字
HEADER_SIZE = 16                     # 帧头固定16字节
ASDU_FORMAT_JSON = 0x01              # JSON格式位
ASDU_FORMAT_XML = 0x00               # XML格式位
```

**对应官方文档**：`docs/official/山猫M20basic_server通信协议总览.md` §1.5

### messages.py — PatrolDevice 消息模型

**职责**：实现 V1.2.1 §1.1.6 定义的 PatrolDevice JSON/XML 信封编解码。

**核心结构**：
```python
PatrolMessage(
    message_type: int,      # Type: 100, 1002, 1003, 1004, 1007, 1101, 2002
    command: int,           # Command: 1, 2, 3, 4, 5, 6...
    sent_at: str,           # 时间戳
    items: dict[str, Any],  # 业务字段
    message_id: int = 0,    # 报文ID（请求/响应关联）
)
```

**对应官方文档**：`docs/official/山猫M20basic_server通信协议总览.md` §接口字典

---

## robot/ — 机器人交互层

### basic_client.py — TCP 客户端

**职责**：与 AOS basic_server 建立 TCP 连接，发送/接收消息，提供安全门禁。

**核心方法**：
- `connect(*, read_only=False)` — 建立真实连接；`read_only=True` 允许状态订阅（不发送控制命令）
- `connect_for_test()` — 测试用回环连接
- `send_read_only(message)` — 仅在显式测试/授权 transport 配置下发送查询；生产入口禁用 TX
- `send_control(message)` — 发送控制命令（需 control_enabled 门禁）
- `receive_messages()` — 接收主动上报消息
- `close()` — 断开连接

**门禁规则**：
```python
# connect() 必须同时满足：
control_enabled == True
protocol_evidence is approved
firmware_evidence is approved
permission_evidence is approved
```

**生产策略**：`TELEMETRY_TX_ENABLED=false`，不自动发送心跳；客户端按 3 秒新鲜度阈值判定数据过期。

**对应官方文档**：`docs/official/山猫M20basic_server通信协议总览.md` §心跳机制

### status.py — 状态消息解析

**职责**：解析 basic_server 主动上报的状态消息，转换为结构化数据。

**支持的报文类型**：

| Type | Command | 名称 | 频率 | 解析方法 |
|------|---------|------|------|----------|
| 1002 | 3 | ErrorList（异常列表） | 事件驱动 | `_normalize_errors()` |
| 1002 | 4 | MotionStatus（运控状态） | 10Hz | `_normalize_motion()` |
| 1002 | 5 | DeviceStatus（设备状态） | 2Hz | `_normalize_device()` |
| 1002 | 6 | BasicStatus（基础状态） | 2Hz | `_normalize_basic()` |
| 1007 | 1 | 导航状态查询响应 | — | `_parse_navigation_status()` |
| 1007 | 2 | 位置查询响应 | — | `_parse_position()` |
| 1007 | 3 | 导航异常主动上报 | 1Hz（≥V1.1.8） | `_parse_navigation_abnormal()` |
| 2002 | 1 | 导航感知状态查询响应 | — | `_parse_perception()` |
| 1003 | 1 | 导航任务响应 | — | `_parse_navigation_response()` |
| 1004 | 1 | 取消导航响应 | — | `_parse_cancel_response()` |

**导航错误码映射（26个）**：
- `0xA301` — 运动状态异常（软急停、摔倒）
- `0xA302` — 电量低于20%
- `0xA313` — 定位状态持续异常（超过30s）
- `0xA400`~`0xA40F` — 导航模块各异常

**对应官方文档**：
- `docs/official/山猫M20软件开发指南V1.2.1.md` §1.3
- `docs/official/山猫M20错误码与异常处理.md`

---

## navigation/ — 导航业务层

### v010.py — 导航报文构造

**职责**：构造 V1.2.1 §1.4.4-1.4.6 定义的导航相关报文，并在发送前执行安全门控检查。

**核心类**：
```python
NavigationSafetySnapshot(
    control_enabled: bool,
    field_authorization: str,
    tcp_connected: bool,
    location_normal: bool,
    obstacle_avoidance_active: bool,
    hard_estop_active: bool,
    protective_fault_active: bool,
    battery_percent: int,
    active_task: bool,
)

SinglePointNavigation(
    value: int,     # 任务值
    map_id: int,    # 地图ID
    pos_x: float,   # X坐标
    pos_y: float,   # Y坐标
    pos_z: float,   # Z坐标
    angle_yaw: float,  # 朝向
)
```

**构造方法**：
- `to_message(safety, sent_at)` → PatrolMessage — 构造 1003/1 导航下发报文
- `build_cancel_navigation_message(safety, sent_at)` → PatrolMessage — 构造 1004/1 取消报文
- `build_navigation_status_query(safety, sent_at)` → PatrolMessage — 构造 1007/1 状态查询报文

**步态常量（V1.2.1格式）**：
```python
GAIT_FLAT_AGGRESSIVE = 0x3002   # 平地敏捷
GAIT_STAIRS_AGGRESSIVE = 0x3003 # 楼梯敏捷
GAIT_FLAT_STANDARD = 0x1001     # 基础标准
GAIT_PLATFORM_STANDARD = 0x1002 # 高台标准
```

**对应官方文档**：
- `docs/official/山猫M20软件开发指南V1.2.1.md` §1.4.4-1.4.6
- `docs/official/山猫M20导航任务下发.md`

---

## video/ — 视频流管理层

### video_manager.py — 视频流管理

**职责**：管理前后相机 RTSP 地址和连接状态。

**官方 RTSP 地址（候选值）**：
```
前相机：rtsp://10.21.31.103:8554/video1
后相机：rtsp://10.21.31.103:8554/video2
```

**状态机**：`DISCONNECTED → CONNECTING → CONNECTED / ERROR`

**对应官方文档**：`docs/official/山猫M20软件开发指南V1.2.1.md` 附录3

### ws_handler.py — WebSocket 视频流处理

**职责**：通过 WebSocket 向前端推送视频流数据。

---

## dashboard_realtime.py — 实时仪表盘

**职责**：连接真实 AOS basic_server，显示实时状态。

**特点**：
- 连接 AOS TCP 30001
- 生产入口不发送心跳，`TELEMETRY_TX_ENABLED=false`
- 绑定 manifest 指定的 `10.21.31.104:8080`
- 返回 `source=REAL`；无真实消息时返回 `NO_DATA`/`STALE`/`ERROR`

**启动方式**：
```bash
# 唯一方式：在 GOS 本机执行
bash deploy/scripts/deploy-readonly.sh --one-shot
```

---

## 测试对应关系

| 代码模块 | 测试文件 |
|----------|----------|
| protocol/frame.py | `test_frame.py` |
| protocol/messages.py | `test_messages.py` |
| robot/status.py | `test_status.py` |
| robot/basic_client.py | `test_basic_client.py` |
| navigation/v010.py | `test_navigation_v010.py` |
| dashboard_realtime.py | `test_dashboard.py` |
