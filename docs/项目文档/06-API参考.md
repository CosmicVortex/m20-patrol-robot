# API 参考文档

**版本**: V1.2  
**更新**: 2026-08-18  

**基础地址**: `http://10.21.31.104:8080`（GOS部署后）  
**认证**: 除 `/api/v1/health` 外，其余接口均需登录后访问（自动登录模式已启用）

---

## 1. 健康检查

### GET /api/v1/health

服务健康检查接口，无需认证。

**响应示例**:
```json
{
  "service": "m20-patrol-web",
  "runtime_mode": "realtime_readonly",
  "read_only_mode": false,
  "control_enabled": true,
  "source": "REAL",
  "connected": true,
  "valid_frames": 1523
}
```

---

## 2. 认证接口

### POST /api/v1/auth/login

用户登录。

**请求体**:
```json
{"username": "admin", "password": "<your_password>"}
```

**响应**:
```json
{"session_id": "abc123...", "username": "admin", "role": "admin"}
```

### POST /api/v1/auth/logout

注销当前会话。

### GET /api/v1/auth/me

获取当前用户信息。

---

## 3. 状态接口

### GET /api/v1/status/latest

获取最新遥测状态数据，2秒轮询。

**响应字段**:
- `source`: 数据来源（REAL/SIMULATED/NO_DATA/ERROR）
- `connected`: TCP连接状态
- `basic`: 基础状态（电量、急停、版本等）
- `motion`: 运动状态（姿态、速度、里程）
- `device`: 设备状态（电池、温度、LED）
- `errors`: 错误列表
- `nav_status`: 导航状态
- `position`: 位置信息

---

## 4. 运动控制接口

### POST /api/v1/motion/state

切换运动状态（0=空闲, 1=站立, 2=急停, 4=趴下, 17=RL控制）。

### POST /api/v1/motion/gait

步态切换（4097=基础, 4099=楼梯, 12290=平地敏捷, 12291=楼梯敏捷）。

### POST /api/v1/motion/axis

轴控制（前进/后退/转向）。

**请求体**:
```json
{"x": 0.5, "y": 0, "yaw": 0}
```

### POST /api/v1/motion/mode

使用模式切换（0=常规, 1=导航, 2=辅助）。

### POST /api/v1/motion/light

照明控制。

### POST /api/v1/motion/charge

充电控制。

### POST /api/v1/motion/sleep

休眠控制。

### POST /api/v1/motion/authorize

授权运动控制。

### POST /api/v1/motion/deauthorize

撤销授权。

### GET /api/v1/motion/status

获取当前运动状态（姿态、速度、里程等）。

**响应字段**:
- `motion_state`: 运动状态（0=空闲,1=站立,2=软急停,4=趴下,17=RL控制）
- `gait`: 当前步态
- `roll`, `pitch`, `yaw`: 姿态角
- `linear_x`, `linear_y`, `omega_z`: 线速度和角速度
- `height`: 当前高度
- `distance`: 累计里程

---

紧急停止。

---

## 5. 导航控制接口

### POST /api/v1/navigation/authorize

授权导航。

### POST /api/v1/navigation/deauthorize

撤销授权。

### POST /api/v1/navigation/tasks

发送导航任务。

**请求体**:
```json
{
  "pos_x": 1.0,
  "pos_y": 0.0,
  "pos_z": 0.0,
  "angle_yaw": 0.0,
  "map_id": 0
}
```

### POST /api/v1/navigation/cancel

取消导航。

### GET /api/v1/navigation/status

查询导航状态。

---

## 6. 云台控制接口

### POST /api/v1/gimbal/connect

连接云台设备。

**请求体**:
```json
{"host": "10.21.31.108", "password": "<your_password>"}
```

### GET /api/v1/gimbal/state

获取云台状态。

### POST /api/v1/gimbal/move

方向控制（up/down/left/right）。

**请求体**:
```json
{"direction": "up", "speed": 5}
```

### POST /api/v1/gimbal/zoom

变倍控制（1-10）。

### POST /api/v1/gimbal/angle

角度控制。

**请求体**:
```json
{"pan": 0, "tilt": 0}
```

### GET /api/v1/gimbal/scan

查询已配置云台地址。

### GET /api/v1/gimbal/device/info

获取云台设备信息。

### GET /api/v1/gimbal/video

获取云台视频流地址。

---

## 7. 视频管理接口

### GET /api/v1/video

视频状态。

### POST /api/v1/video/config

配置RTSP地址。

### POST /api/v1/video/probe

探测视频流。

### POST /api/v1/video/start

启动视频流。

### POST /api/v1/video/stop

停止视频流。

### GET /api/v1/video/playback/{source}

视频回放。

---

## 8. 业务管理接口

### GET /api/v1/work-orders

工单列表。

### POST /api/v1/work-orders

创建工单。

### PUT /api/v1/work-orders/

更新工单（路径末尾斜杠后跟ID，请求体传id字段）

**示例**: `PUT /api/v1/work-orders/VO-2026-001`

### GET /api/v1/inspection-points

巡检点列表。

### GET /api/v1/timeline

时间线数据。

---

## 9. 系统管理接口

### GET /api/v1/users

用户列表。

### PUT /api/v1/users/password

修改密码。

### GET /api/v1/system/info

系统信息。

### GET /api/v1/devices

设备列表。

### POST /api/v1/devices

创建设备。

### DELETE /api/v1/devices/

删除设备（路径末尾斜杠后跟ID）

**示例**: `DELETE /api/v1/devices/DEV-2026-001`

---

*完整实现详见 [03-核心模块实现](./03-核心模块实现.md) 和 [07-协议对齐说明](./07-协议对齐说明.md)*
