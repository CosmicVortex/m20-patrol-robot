# 02 — 系统架构

## 当前可交付架构

```
开发机 / GOS (10.21.31.104，候选值)
  │
  ├─ backend.app.protocol       APDU/ASDU 离线编解码
  │     ├── frame.py             16字节帧编解码、拆包/粘包
  │     └── messages.py          PatrolDevice JSON/XML 信封
  │
  ├─ backend.app.robot          机器人交互层
  │     ├── basic_client.py      TCP客户端、门禁、message_id关联
  │     └── status.py            状态消息解析
  │
  ├─ backend.app.navigation     导航业务层
  │     └── v010.py              导航报文构造、安全门控
  │
  ├─ backend.app.video          视频流管理
  │     ├── video_manager.py     RTSP地址管理、状态追踪
  │     └── ws_handler.py        WebSocket视频流处理
  │
  ├─ backend.app.dashboard      Web仪表盘（模拟只读，绑定127.0.0.1）
  │
  └─ deploy/
        ├── scripts/install-gos.sh    GOS安装脚本
        ├── scripts/rollback-gos.sh   回滚脚本
        └── systemd/m20-patrol-readonly.service  systemd服务

现场机器人网络（当前不连接）
  ├─ AOS (10.21.31.103)          basic_server、运动控制
  │     UDP 30000 / TCP 30001
  └─ NOS (10.21.31.106)          建图、定位、导航
```

当前代码包含仅用于离线验证的 TCP 传输原语和导航报文构造器，但没有真实状态聚合、视频转码器、巡逻状态机或实机发送放行。GOS 部署服务仍只显示模拟状态。

## 目标架构

```
浏览器
   │ 仅连接 GOS
   ▼
GOS
  ├─ 只读状态服务（TCP → AOS basic_server）
  ├─ 视频网关（RTSP → HLS/WebRTC → 浏览器）
  ├─ 地图副本服务（NOS → GOS）
  └─ 经放行的导航服务
       │
       ├─ AOS basic_server：状态订阅 + 任务下发
       └─ NOS：地图、定位、规划

控制边界：
  ├─ 控制能力独立于只读服务，默认关闭
  ├─ 导航发送需书面放行
  └─ 所有控制操作记录审计日志
```

目标架构在需求 R-06 至 R-09 的准入条件全部满足后才可逐项建设。

## 主机角色

| 主机 | IP（候选） | 职责 | SSH/VNC |
|---|---|---|---|
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
|---|---|---|---|
| basic_server TCP | APDU/ASDU JSON | 30001 | 任务下发、状态订阅（推荐） |
| basic_server UDP | APDU/ASDU JSON | 30000 | 高频速度指令（≥20Hz） |
| RTSP | H.265/H.264 | 8554 | 本体前后相机视频 |
| Web HTTP | JSON | 8080 | 状态查询、控制请求 |
| Web WebSocket | — | 8080 | 状态推送、视频流 |
| ROS2/DDS | FastDDS | 动态 | 话题订阅（GOS内部） |

## 版本规则

协议字段的实现依据必须写明具体文件和页码。当前 `frame.py` 的布局来自受控《山猫 M20 系列软件开发手册》V0.1.0 第 6–8 页；它尚未作为《软件开发指南》V1.2.1 或当前固件的实机协议事实确认。真实接入前必须重新核对。

详见 [04-requirements.md](./04-requirements.md)。
