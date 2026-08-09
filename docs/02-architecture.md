# 02 — 系统架构

## 当前架构

```
浏览器
   │ 仅连接 GOS
   ▼
GOS (10.21.31.104)
  │
  ├─ backend.app.protocol       APDU/ASDU 离线编解码
  │     ├── frame.py             16字节帧编解码、拆包/粘包
  │     └── messages.py          PatrolDevice JSON/XML 信封
  │
  ├─ backend.app.robot          机器人交互层
  │     ├── basic_client.py      TCP客户端、门禁、message_id关联
  │     ├── status.py            状态消息解析（1002/3,4,5,6; 1007/1,2,3; 2002/1）
  │     └── telemetry.py         真实状态订阅（TCP → AOS basic_server）
  │
  ├─ backend.app.navigation     导航业务层
  │     ├── v010.py              导航报文构造、安全门控
  │     ├── service.py           导航控制服务（Web授权）
  │     └── ws_handler.py        导航WebSocket处理器
  │
  ├─ backend.app.video          视频流管理
  │     ├── video_manager.py     RTSP地址管理、状态追踪
  │     ├── stream_manager.py    RTSP流管理（ffprobe探测、FFmpeg拉流）
  │     └── ws_handler.py        WebSocket视频流处理
  │
  └─ backend.app.dashboard_realtime  唯一实时仪表盘入口（连接真实AOS；默认只读）
       │
       ├─ TCP 30001 → AOS basic_server（状态订阅）
       ├─ RTSP 8554 → 本体前后相机（待实测）
       └─ Web 8080 → 浏览器（非控制状态展示）

现场机器人网络（当前不连接）
  ├─ AOS (10.21.31.103)          basic_server、运动控制
  │     UDP 30000 / TCP 30001
  └─ NOS (10.21.31.106)          建图、定位、导航
```

### 已实现功能

| 功能 | 状态 | 说明 |
|------|------|------|
| APDU/ASDU 编解码 | ✅ | 16字节帧头，JSON/XML 信封 |
| 状态消息解析 | ✅ | 1002/3,4,5,6 + 1007/1,2,3 + 2002/1 |
| TCP 客户端 + 门禁 | ✅ | control_enabled 默认 False |
| 真实状态订阅 | ✅ | TelemetryAdapter 连接 AOS TCP 30001，read_only 模式 |
| 实时仪表盘 | ✅ | `realtime_readonly`，绑定 manifest 指定的 GOS 地址 |
| 历史仪表盘入口 | ⚠️ | 兼容保留，不得由 one-shot 或默认 systemd unit 调用 |
| 导航报文构造 | ✅ | Gait=0x3002，安全门控 |
| 导航控制服务 | ✅ | Web 授权，审计日志 |
| 视频管理器 | 🟡 | RTSP 地址已配置，拉流待实测 |
| 多点巡逻状态机 | 🔴 | 需单点控制验收后 |

### 未实现功能

- 多点巡逻状态机（R-09）
- 云台适配（R-10）
- 视频转码代理（需 GOS FFmpeg 实测）

## 目标架构

```
浏览器
   │ 仅连接 GOS
   ▼
GOS
  ├─ 只读状态服务（TCP → AOS basic_server）✅ 已实现
  ├─ 视频网关（RTSP → HLS/WebRTC → 浏览器）🟡 基础框架
  ├─ 地图副本服务（NOS → GOS）🔴 未实现
  └─ 经放行的导航服务 ✅ 已实现（Web授权）
       │
       ├─ AOS basic_server：状态订阅 + 任务下发
       └─ NOS：地图、定位、规划
```

控制边界：
- 控制能力独立于只读服务，默认关闭
- 导航发送需书面放行
- 所有控制操作记录审计日志

目标架构在需求 R-06 至 R-09 的准入条件全部满足后才可逐项建设。

## 主机角色

| 主机 | IP | 职责 | SSH/VNC |
|------|-----|------|---------|
| AOS | 10.21.31.103 | 运动控制、basic_server、rl_deploy | ❌ 不可访问 |
| NOS | 10.21.31.106 | 建图、定位、导航、planner | ✅ 可访问 |
| GOS | 10.21.31.104 | 用户二次开发、Web服务 | ✅ 可访问 |

AOS 不提供 SSH/VNC 访问，用户不应直接操作 AOS。

## 数据与控制边界

- AOS/NOS 原厂服务、网络路由和原始地图不由项目程序修改
- GOS 只读取经核验的地图副本
- 模拟状态必须标识 `SIMULATED`，不得显示为真实设备状态
- 未经版本、权限、真实样本和安全放行确认，不建立 AOS 连接，不发送心跳或控制报文
- 控制能力必须独立于只读服务，默认关闭并 fail-closed
- 现场测试优先使用官方 APP/遥控器，项目程序不介入运动控制

## 协议接口

| 接口 | 协议 | 端口 | 用途 |
|------|------|------|------|
| basic_server TCP | APDU/ASDU JSON | 30001 | 任务下发、状态订阅（推荐） |
| basic_server UDP | APDU/ASDU JSON | 30000 | 高频速度指令（≥20Hz） |
| RTSP | H.265/H.264 | 8554 | 本体前后相机视频 |
| Web HTTP | JSON | 8080 | 状态查询、控制请求 |
| Web WebSocket | — | 8080 | 状态推送、视频流 |
| ROS2/DDS | FastDDS | 动态 | 话题订阅（GOS内部） |

## 版本规则

协议字段的实现依据必须写明具体文件和页码。当前 `frame.py` 的布局来自受控《山猫 M20 系列软件开发手册》V0.1.0 第 6–8 页；它尚未作为《软件开发指南》V1.2.1 或当前固件的实机协议事实确认。真实接入前必须重新核对。

详见 [04-requirements.md](./04-requirements.md)。
