# M20 Pro Web 真实功能开发契约

**状态：** contract_drafted / real_web_api_not_implemented / 未完成现场验收  
**依据优先级：** 用户确认的现场输出 > 官方资料 > 代码实现 > 离线测试  
**协议优先依据：**《山猫M20软件开发指南》V1.2.1（2026-05-18）

## 1. 目标

将当前演示页面升级为真实 Web 应用：真实遥测、真实登录与权限、真实导航/运动控制、真实视频、真实截图/录像、真实设备和数据管理。任何未接入现场或未取得接口证据的能力必须显示 `UNVERIFIED` 或 `BLOCKED`，不得使用随机数、示例记录或伪造在线状态。

## 2. 已确认的代码与文档事实

| 范围 | 当前事实 | 依据 |
|---|---|---|
| APDU/ASDU | 已有 JSON/XML 编解码和 M20 V0.1.0 帧布局 | `backend/app/protocol/*` |
| 状态 | 已解析 1002/3、1002/4、1002/5、1002/6、1007/1、1007/2、1007/3、2002/1 | `backend/app/robot/status.py` |
| 导航 | 已有 1003/1、1004/1、1007/1 报文构造及安全快照 | `backend/app/navigation/v010.py` |
| 运动 | 官方文档定义 Type=2 Cmd=21/22/23/25；当前代码尚未完成这些命令构造与真实 Web 接入 | 官方运动控制协议、现有代码 |
| 状态订阅 | AOS basic_server TCP 30001，UDP 30000；真实 TCP 适配器已有 | `basic_client.py`, `telemetry.py` |
| 视频 | V1.2.1 给出默认 RTSP `rtsp://10.21.31.103:8554/video1` 与 `video2`；代码默认地址仍为空，现场仍需确认可达性、鉴权和编码 | `video/stream_manager.py`、V1.2.1 §附录3 |
| Web | 当前单文件页面已接 `/api/v1/status/latest`；认证、媒体 API、控制 API、数据持久化尚未接入，以下接口均为 planned/not_implemented | `docs/website/index.html` |
| 配置 | `deploy/readonly-manifest.json` 当前为状态订阅模式，禁止控制发送 | manifest |

## 3. 现场前置条件（未满足不得宣称真实完成）

1. 用户在本地笔记本/GOS 执行现场预检并返回完整原始输出。
2. 确认实际机器人型号为 M20 Pro，并返回 GOS/AOS/NOS 软件、固件和协议服务版本。
3. 确认 AOS basic_server TCP/UDP 监听、权限和报文收发样本。
4. 控制功能放行前，负责人提供现场授权证据、急停可用性、定位正常、避障正常、无活动任务、电量及安全区域确认；安全快照必须带采样时间和 freshness，不得使用过期快照。
5. 视频功能放行前，返回现场 RTSP URL、鉴权方式、编解码、分辨率、帧率和 ffprobe 原始输出。
6. 截图/录像放行前，确认浏览器可用播放格式、存储位置、保留策略和磁盘容量。
7. 账户功能放行前，确认初始管理员创建方式、密码策略、会话时长、角色权限和审计保留策略。

## 4. 后端真实接口契约

### 认证与账户

- `POST /api/v1/auth/login`：账号密码登录，返回短期会话令牌；失败不泄露账号是否存在。
- `POST /api/v1/auth/logout`：撤销当前会话。
- `GET /api/v1/auth/me`：当前用户和权限。
- `GET/POST/PATCH /api/v1/users`：需管理员权限，密码只存强哈希，禁止明文。
- 所有控制、设备变更、数据导出接口必须鉴权并写审计日志。

### 设备与遥测

- `GET /api/v1/health`
- `GET /api/v1/status/latest`
- `GET /api/v1/devices`
- `GET /api/v1/devices/{id}`
- `GET /api/v1/navigation/status`

数据源状态必须使用：`NO_DATA`、`API_ERROR`、`REAL_STALE`、`REAL_FRESH`、`INVALID_PAYLOAD`。不能使用示例状态替代真实数据。

### 导航与运动

所有控制接口默认返回 HTTP `403`，错误码为 `BLOCKED`；WebSocket 使用等价结构化错误码。只有运行时配置、现场证据、已认证用户角色、短时授权租约和实时安全快照同时满足才可发送：

- `POST /api/v1/navigation/authorize`
- `POST /api/v1/navigation/deauthorize`
- `POST /api/v1/navigation/tasks` → Type=1003 Cmd=1
- `POST /api/v1/navigation/cancel` → Type=1004 Cmd=1
- `GET /api/v1/navigation/status` → Type=1007 Cmd=1
- `POST /api/v1/motion/state` → Type=2 Cmd=22
- `POST /api/v1/motion/gait` → Type=2 Cmd=23
- `POST /api/v1/motion/velocity` → Type=2 Cmd=21 或 Cmd=25

控制输入必须包含并校验 `Value`、`MapID`、`PosX`、`PosY`、`PosZ`、`AngleYaw`、`PointInfo`、`Gait`、`Speed`、`Manner`、`ObsMode`、`NavMode` 等官方字段；仅 M20 Pro 导航能力可按适用软件包放行。必须校验类型、范围、当前 MotionState、ControlUsageMode、定位、避障、急停、保护故障、电量和活动任务，并拒绝未知或过期安全字段。检查与发送必须在同一控制锁/租约内完成。

速度控制的 Cmd=21/25、单位、范围和 500ms 超时规则必须按各自官方文档版本及现场软件包确认；V1.2.1 与 V1.0.0 运动控制文档不得混写为同一版本依据。高频速度指令由服务端 20Hz 调度，WebSocket/客户端/TCP/UDP 断开、租约过期或进程异常时必须立即停止发送并进入安全状态。Web 页面不得自行拼装协议报文。

### 视频、截图和录像

- `GET /api/v1/video/streams`
- `POST /api/v1/video/{source}/probe`
- `POST /api/v1/video/{source}/start`
- `POST /api/v1/video/{source}/stop`
- `POST /api/v1/video/{source}/screenshot`
- `POST /api/v1/video/{source}/recordings`
- `GET /api/v1/recordings`
- `GET /api/v1/recordings/{id}`
- `GET /api/v1/recordings/{id}/download`

官方默认 RTSP 地址可作为配置初始值，但不能作为当前设备实测事实。前端不得获得含用户名、密码或临时令牌的 RTSP URL；服务端必须提供短期媒体会话 URL、代理 ID 或 WebRTC/HLS 地址。媒体状态至少区分 `CONFIGURED`、`PROBING`、`RTSP_CONNECTED`、`FIRST_FRAME_RECEIVED`、`TRANSCODING`、`BROWSER_PLAYABLE`、`STALE`、`ERROR`、`STOPPED`。只有真实首帧和浏览器播放管线成功后才可显示在线；只有服务端真实生成文件并返回可验证 ID 后才可显示截图/录像成功。文件下载必须鉴权、防路径穿越、防 ID 枚举并执行存储配额和保留策略。

## 5. 开发顺序

1. API 服务骨架、配置加载、统一错误格式、认证和审计。
2. 真实遥测与设备查询接入，前端替换当前演示入口。
3. 视频探测、转码/浏览器播放、截图、录像和存储清理。
4. 导航状态查询与授权流程。
5. 导航下发/取消；现场证据满足后才允许运行时开启。
6. 运动状态/步态/速度接口；逐项现场放行，默认关闭。
7. Web 六页面真实数据绑定、权限控制、错误/空态、响应式优化。
8. 单元、集成、API、媒体、浏览器和现场门禁；独立子代理审查，修复后复审，最多三轮。

## 6. 状态定义

- `planned`：目标契约已定义，代码尚不存在。
- `not_implemented`：功能尚未实现，不得在 Web 中显示成功状态。
- `implemented`：代码存在。
- `offline_verified`：云端离线测试通过。
- `runtime_integrated`：服务已连接真实目标并有原始输出。
- `field_verified`：真实现场功能验证通过。
- `field_accepted`：负责人现场放行并签收。
- `unverified`：缺现场证据。
- `blocked`：安全、配置、依赖或接口条件不满足。

当前真实 Web 项目整体状态：`contract_drafted / code_components_present / real_web_api_not_implemented / control_field_blocked / video_capture_recording_not_implemented / runtime_integrated pending / field_verified pending / field_accepted pending`。
