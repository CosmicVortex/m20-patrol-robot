# 02 — 系统架构

## 架构图

```
浏览器
   │ 仅连接 GOS
   ▼
GOS (10.21.31.104)
  ├─ backend.app.protocol    APDU/ASDU编解码
  ├─ backend.app.robot       TCP客户端、状态解析、遥测
  ├─ backend.app.navigation  导航报文构造、安全门控
  ├─ backend.app.video       RTSP管理、视频流
  └─ backend.app.server      Web服务入口（8080）
       │
       ├─ TCP 30001 → AOS basic_server（状态订阅）
       └─ RTSP 8554 → 本体前后相机（待实测）

现场机器人网络
  ├─ AOS (10.21.31.103)   basic_server、运动控制
  └─ NOS (10.21.31.106)   建图、定位、导航
```

## 已实现

| 功能 | 状态 | 文件 |
|------|------|------|
| APDU/ASDU编解码 | ✅ | `protocol/frame.py` |
| 状态消息解析 | ✅ | `robot/status.py` |
| TCP客户端+门禁 | ✅ | `robot/basic_client.py` |
| 实时状态订阅 | ✅ | `robot/telemetry.py` |
| 实时仪表盘 | ✅ | `dashboard_realtime.py` |
| 导航报文构造 | ✅ | `navigation/v010.py` |
| Web服务入口 | ✅ | `server.py` |
| 认证模块 | ✅ | `auth/` |

## 未实现

- 多点巡逻状态机
- 云台适配
- 视频转码代理（需FFmpeg实测）

## 主机角色

| 主机 | IP | 职责 | 访问 |
|------|-----|------|------|
| GOS | 10.21.31.104 | Web服务、二次开发 | SSH/VNC ✅ |
| AOS | 10.21.31.103 | 运动控制、basic_server | ❌ 不可访问 |
| NOS | 10.21.31.106 | 建图、定位、导航 | SSH/VNC ✅ |
| 云端开发机 | 局域网 | 代码开发、测试 | Git ✅ |

## 协议接口

| 接口 | 端口 | 用途 |
|------|------|------|
| basic_server TCP | 30001 | 状态订阅、任务下发 |
| basic_server UDP | 30000 | 高频速度指令（≥20Hz） |
| RTSP | 8554 | 本体前后相机视频 |
| Web HTTP | 8080 | 状态查询、控制请求 |

## 安全边界

- 控制能力独立于状态订阅，默认关闭
- 导航/运动需书面放行
- 所有控制操作记录审计日志
- 模拟状态标识 `SIMULATED`，不得显示为真实
