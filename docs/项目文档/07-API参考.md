# API 参考文档

本文档详细列出所有HTTP API接口，基于 `router.py` 路由注册与 Handler 实现。
> 
> **基础地址**: `http://10.21.31.104:8080`（GOS部署后）
> 
> **认证**: 除 `/api/v1/health` 外，其余接口均需登录后访问（自动登录模式已启用）

---

## 1. 健康检查

### GET /api/v1/health

服务健康检查接口，无需认证。

**响应示例**:
```json
{
  "service": "m20-patrol-web",
  "runtime_mode": "realtime",
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
{
  "username": "admin",
  "password": "<your_password>"
}
```

**响应**:
```json
{
  "session_id": "abc123...",
  "username": "admin",
  "role": "admin"
}
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
```json
{
  "source": "REAL",
  "connected": true,
  "received_at": "2026-08-16T10:00:00Z",
  "age_ms": 150,
  "basic": {
    "batt1": 92,
    "batt2": 88,
    "hes": 0,
    "state": 1
  },
  "motion": {
    "vx": 0.0,
    "vy": 0.0,
    "vz": 0.0
  },
  "errors": []
}
```

---

## 4. 运动控制接口

### POST /api/v1/motion/state

切换运动状态。

**请求体**:
```json
{"state": "stand"}  // stand / lie_down / soft_estop
```

### POST /api/v1/motion/gait

切换步态。

**请求体**:
```json
{"gait": 4097}  // 4097=基础, 4099=楼梯, 12290=平地敏捷, 12291=楼梯敏捷
```

### POST /api/v1/motion/axis

轴控制（方向+速度）。

**请求体**:
```json
{"x": 0.5, "y": 0, "yaw": 0}
// x: 前后 (-1~1), y: 左右 (-1~1), yaw: 偏航 (-1~1)
```

### POST /api/v1/motion/light

照明控制。

**请求体**:
```json
{"front": 1, "back": 1}  // 1=开, 0=关
```

### POST /api/v1/motion/mode

使用模式切换。

**请求体**:
```json
{"mode": 0}  // 0=常规, 1=导航, 2=辅助
```

### POST /api/v1/motion/charge

充电控制。

**请求体**:
```json
{"charge": 1}  // 1=开始充电, 0=停止
```

### POST /api/v1/motion/sleep

休眠控制。

**请求体**:
```json
{"sleep": false, "auto": false, "time": 10}
```

### GET /api/v1/motion/status

获取当前运动状态。

### POST /api/v1/motion/authorize

授权运动控制。

**请求体**:
```json
{"operator": "admin"}
```

### POST /api/v1/motion/deauthorize

撤销授权。

### POST /api/v1/emergency/stop

紧急停止。

---

## 5. 导航控制接口

### POST /api/v1/navigation/authorize

授权导航控制。

**请求体**:
```json
{"operator": "admin"}
```

### POST /api/v1/navigation/deauthorize

撤销导航授权。

### POST /api/v1/navigation/tasks

发送单点导航任务。

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

> **注意**: API参数使用 snake_case，与官方协议 PascalCase 的转换发生在 `navigation/protocol.py` 的 `to_message()` 方法中。

### POST /api/v1/navigation/cancel

取消当前导航任务。

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

获取云台当前状态。

### POST /api/v1/gimbal/move

方向控制。

**请求体**:
```json
{"direction": "up", "speed": 5}
// direction: up/down/left/right
// speed: 1-10
```

### POST /api/v1/gimbal/zoom

变倍控制。

**请求体**:
```json
{"level": 1.5}
// level: 1-10，浮点数
```

### POST /api/v1/gimbal/angle

角度控制（pan+tilt）。

**请求体**:
```json
{"pan": 0, "tilt": 0}
```

### GET /api/v1/gimbal/scan

**注意**: 此接口为 GET，无请求体，仅返回已配置云台地址。

### GET /api/v1/gimbal/device/info

获取设备信息。

### GET /api/v1/gimbal/video

获取视频流地址。

---

## 7. 视频管理接口

### GET /api/v1/video

获取视频状态。

### POST /api/v1/video/config

配置RTSP地址。

**请求体**:
```json
{
  "front_wide": "rtsp://10.21.31.103:8554/video1",
  "rear_wide": "rtsp://10.21.31.103:8554/video2",
  "thermal": "rtsp://10.21.31.108:554/stream1",
  "gimbal": "rtsp://10.21.31.108:554/stream2"
}
```

### POST /api/v1/video/probe

探测视频流（共用 VideoStreamControlHandler）。

### POST /api/v1/video/start

启动视频流（共用 VideoStreamControlHandler）。

### POST /api/v1/video/stop

停止视频流（共用 VideoStreamControlHandler）。

> **注**: `/api/v1/video/probe`、`/api/v1/video/start`、`/api/v1/video/stop` 三个路径共用 `VideoStreamControlHandler`，通过请求路径区分操作。

### GET /api/v1/video/playback/{source}

视频回放。

**路径参数**: `source` 为视频源名称（front_wide/rear_wide/thermal/gimbal）。

---

## 8. 工单管理接口

### GET /api/v1/work-orders

获取工单列表。

**查询参数**:
- `status`: 过滤状态（pending/processing/resolved）
- `limit`: 返回数量（默认20）

### POST /api/v1/work-orders

创建工单。

**请求体**:
```json
{
  "title": "异常告警",
  "description": "检测到异常目标",
  "severity": "warning",
  "source": "error_code"
}
```

### PUT /api/v1/work-orders/

更新工单（末尾有斜杠）。

**请求体**:
```json
{
  "id": 1,
  "status": "resolved",
  "description": "已处理"
}
```

> **别名**: `POST /api/v1/work-orders/create` 和 `PUT /api/v1/work-orders/update` 为历史别名，建议使用标准 RESTful 路径。

---

## 9. 巡检点接口

### GET /api/v1/inspection-points

获取巡检点列表。

**响应示例**:
```json
[
  {
    "id": 1,
    "name": "入口岗亭",
    "pos_x": 1.5,
    "pos_y": 2.3,
    "pos_z": 0.0,
    "angle_yaw": 0.0
  }
]
```

---

## 10. 用户管理接口

### GET /api/v1/users

获取用户列表。

### PUT /api/v1/users/password

修改密码。

**请求体**:
```json
{
  "username": "admin",
  "old_password": "xxx",
  "new_password": "yyy"
}
```

---

## 11. 设备管理接口

### GET /api/v1/devices

获取设备列表。

### POST /api/v1/devices

创建设备。

**请求体**:
```json
{
  "name": "新设备",
  "type": "camera",
  "ip": "10.21.31.200"
}
```

### DELETE /api/v1/devices/

删除设备（末尾有斜杠）。

**请求体**:
```json
{"id": 1}
```

---

## 12. 系统接口

### GET /api/v1/system/info

获取系统信息。

**响应示例**:
```json
{
  "version": "V1.1.5",
  "uptime_seconds": 3600,
  "python_version": "3.8.10",
  "runtime_mode": "realtime_readonly"
}
```

### GET /api/v1/timeline

获取时间线数据。

**查询参数**:
- `hours`: 时间范围（小时，默认24）

---

## 附录A：错误码

| HTTP状态码 | 含义 |
|-----------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限（控制未启用或需管理员） |
| 404 | 接口不存在 |
| 500 | 服务器内部错误 |

## 附录B：运动状态值

| 值 | 名称 | 说明 |
|----|------|------|
| 0 | 空闲 | 静止状态 |
| 1 | 站立 | Stand up |
| 2 | 软急停 | Soft estop |
| 4 | 趴下 | Lie down |
| 17 | RL控制 | 远程操控模式 |

## 附录C：步态值

| 十六进制 | 十进制 | 名称 | 适用场景 |
|----------|--------|------|----------|
| 0x1001 | 4097 | 基础 | 室内平坦地面 |
| 0x1003 | 4099 | 楼梯 | 台阶/路沿 |
| 0x3002 | 12290 | 平地敏捷 | 自主导航+平地 |
| 0x3003 | 12291 | 楼梯敏捷 | 自主导航+台阶 |

---

**文档版本**: V1.1.5  
**最后更新**: 2026-08-16
