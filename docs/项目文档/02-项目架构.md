# 系统架构

## 架构图

```
浏览器（仅内网访问）
   │
   ▼
GOS (10.21.31.104)
  ├─ backend.app.protocol    APDU/ASDU 编解码
  ├─ backend.app.robot       TCP 客户端、状态解析、遥测
  ├─ backend.app.navigation  导航报文构造、安全门控
  ├─ backend.app.gimbal      云台控制（WEB 2.0 协议）
  ├─ backend.app.video       RTSP 管理、视频流
  └─ backend.app.server      Web 服务入口（端口 8080）
       │
       ├─ TCP 30001 → AOS basic_server（状态订阅）
       └─ HTTP  → 数尔云台（192.168.1.108，待确认）

现场机器人网络
  ├─ AOS (10.21.31.103)   运动控制、basic_server
  ├─ NOS (10.21.31.106)   建图、定位、导航
  └─ 数尔云台 (192.168.1.108)   热成像、可见光相机（待确认）
```

## 已实现功能

| 功能 | 状态 | 实现文件 |
|------|------|----------|
| APDU/ASDU 编解码 | ✅ | `protocol/frame.py`, `protocol/messages.py` |
| 状态消息解析 | ✅ | `robot/status.py` |
| TCP 客户端 + 门禁 | ✅ | `robot/basic_client.py` |
| 实时状态订阅 | ✅ | `robot/telemetry.py` |
| 导航报文构造 | ✅ | `navigation/v010.py` |
| Web 服务入口 | ✅ | `server.py` |
| 认证模块 | ✅ | `auth/` |
| 云台控制（WEB 2.0） | ✅ | `gimbal/adapter.py`, `gimbal/handlers.py` |

## 未实现功能

- 多点巡逻状态机
- 视频转码代理（需 FFmpeg 实测）
- ROS2 话题对接
- UDP 高频运动控制（≥20Hz）

## 主机角色

| 主机 | IP | 职责 | 访问方式 |
|------|-----|------|----------|
| GOS | 10.21.31.104 | Web 服务、二次开发 | SSH/VNC ✅ |
| AOS | 10.21.31.103 | 运动控制、basic_server | ❌ 不可直连 |
| NOS | 10.21.31.106 | 建图、定位、导航 | SSH/VNC ✅ |
| 云端开发机 | 局域网 | 代码开发、测试 | Git ✅ |

## 协议端口

| 接口 | 端口 | 协议 | 用途 |
|------|------|------|------|
| basic_server TCP | 30001 | TCP | 状态订阅、任务下发 |
| basic_server UDP | 30000 | UDP | 高频速度指令（≥20Hz） |
| RTSP | 8554 | TCP | 本体前后相机视频 |
| Web HTTP | 8080 | HTTP | 状态查询、控制请求 |
| 数尔云台 | 80 | HTTP | WEB 2.0 协议控制 |

## 安全边界

- 控制能力独立于状态订阅，默认关闭
- 导航/运动需书面放行
- 所有控制操作记录审计日志
- 模拟状态标识 `SIMULATED`，不得显示为真实
