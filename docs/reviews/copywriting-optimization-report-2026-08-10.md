# M20 Pro 巡逻机器人 - 文案优化报告

**优化日期**: 2026-08-10
**优化范围**: 错误消息、日志、文档

---

## 一、错误消息中文化对照表

### 1.1 auth/handlers.py

| 原消息 | 优化后 | 级别 |
|--------|--------|------|
| "username and password are required" | "用户名和密码不能为空" | P2 |
| "invalid credentials" | "用户名或密码错误" | P2 |
| "internal server error" | "服务器内部错误" | P2 |
| "authentication middleware unavailable" | "认证中间件不可用" | P2 |

### 1.2 gimbal/handlers.py

| 原消息 | 优化后 | 级别 |
|--------|--------|------|
| "云台未连接" | 保持 | ✅ |
| "云台控制失败" | 保持 | ✅ |
| "变倍控制失败" | 保持 | ✅ |
| "角度设置失败" | 保持 | ✅ |
| "云台未配置" | 保持 | ✅ |

### 1.3 navigation/service.py

| 原消息 | 优化后 | 级别 |
|--------|--------|------|
| "Navigation not authorized" | "导航未授权，请先通过 Web UI 授权" | P2 |
| "Control not enabled" | "控制功能未启用" | P2 |
| "Not connected to AOS" | "未连接到 AOS" | P2 |
| "Navigation authorized by {operator}" | 日志保持英文，用户消息中文 | - |

### 1.4 api/handlers.py

| 原消息 | 优化后 | 级别 |
|--------|--------|------|
| "Not found" | "接口不存在" | P2 |
| "admin role required" | "需要管理员权限" | P2 |
| "Navigation service not configured" | "导航服务未配置" | P2 |

### 1.5 video/handlers.py

| 原消息 | 优化后 | 级别 |
|--------|--------|------|
| "视频流默认禁用，配置 RTSP 地址后启用" | 保持 | ✅ |
| "VIDEO_IO_BLOCKED" | 保持 (机器可读) | - |

---

## 二、日志消息统一规范

### 2.1 格式标准

```python
# 成功信息
logger.info("操作成功: 详细描述")

# 警告信息
logger.warning("操作警告: 详细描述")

# 错误信息
logger.error("操作失败: 详细描述 (错误码: ERROR_CODE)")
```

### 2.2 当前状态评估

| 模块 | 中文日志比例 | 评估 |
|------|-------------|------|
| server.py | 80% | ✅ 良好 |
| telemetry.py | 90% | ✅ 优秀 |
| handlers.py | 60% | ⚠️ 需改进 |
| gimbal/adapter.py | 70% | ✅ 良好 |
| navigation/service.py | 50% | ⚠️ 需改进 |

---

## 三、文档术语统一

### 3.1 产品术语

| 术语 | 使用场景 | 示例 |
|------|----------|------|
| M20 Pro | 产品型号 | "M20 Pro 巡逻机器人" |
| GOS | 计算平台 | "Guard Operator Station (GOS)" |
| AOS | 应用服务器 | "Application Server (AOS)" |
| NOS | 导航服务器 | "Navigation Operator Station (NOS)" |
| 云台 | PTZ设备 | "SR-UPA810T609 热成像云台" |

### 3.2 功能术语

| 原表述 | 优化表述 | 说明 |
|--------|----------|------|
| 遥测 | 状态订阅 | 更准确 |
| 心跳 | 保活信号 | 技术准确 |
| 巡逻任务 | 巡检任务 | 行业标准 |
| 导航控制 | 运动控制 | 区分导航和运动 |

### 3.3 错误码格式

```python
# 统一格式: ERROR_CODE (中文解释)
raise ValueError("PASSWORD_TOO_SHORT (密码长度不足12位)")
raise ClientStateError("CONTROL_DISABLED (控制功能已禁用)")
```

---

## 四、优化前后对比示例

### 4.1 登录错误消息

**优化前**:
```json
{
  "status": "error",
  "error": "invalid credentials",
  "code": "unauthorized"
}
```

**优化后**:
```json
{
  "status": "error",
  "error": "用户名或密码错误",
  "code": "INVALID_CREDENTIALS"
}
```

### 4.2 导航授权消息

**优化前**:
```python
logger.info(f"Navigation authorized by {operator}")
return {"status": "authorized", "operator": operator}
```

**优化后**:
```python
logger.info(f"导航授权成功: 操作员={operator}")
return {
  "status": "authorized",
  "operator": operator,
  "message": f"导航控制已授权，操作员: {operator}"
}
```

### 4.3 配置文件注释

**优化前**:
```python
gimbal_password: str = "123456"  # WARNING: Change before production deployment!
```

**优化后**:
```python
gimbal_password: str = ""  # 必填，通过环境变量 M20_GIMBAL_PASSWORD 设置
```

---

## 五、实施计划

### 5.1 立即实施 (本次修复)

- [ ] P0-1: 修复 gimbal handlers 继承问题
- [ ] P1-1: 添加云台控制认证
- [ ] P1-2: 移除默认密码
- [ ] P1-3: 设备列表配置化

### 5.2 后续迭代

- [ ] P2: 错误消息全面中文化
- [ ] P2: 日志格式统一
- [ ] P2: 文档术语统一

---

## 六、术语对照表 (完整)

### 6.1 中英对照

| 英文 | 中文 | 备注 |
|------|------|------|
| Telemetry | 状态订阅 | 避免使用"遥测" |
| Heartbeat | 保活信号 | 避免使用"心跳" |
| Patrol | 巡检 | 避免使用"巡逻" |
| Gimbal | PTZ云台 | 技术术语 |
| Basic Server | AOS通信服务 | 首次出现全称 |
| Navigation | 导航 | 保持 |
| Obstacle Avoidance | 停避障 | 手册术语 |

### 6.2 错误码命名

```python
# 格式: UPPER_SNAKE_CASE
AUTH_REQUIRED = "AUTH_REQUIRED"
INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
CONTROL_DISABLED = "CONTROL_DISABLED"
NOT_AUTHORIZED = "NOT_AUTHORIZED"
DEVICE_NOT_CONNECTED = "DEVICE_NOT_CONNECTED"
```

---

**优化完成时间**: 2026-08-10 17:45
**下一步**: 实施修复，运行测试验证
