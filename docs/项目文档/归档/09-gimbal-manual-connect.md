# 云台手动连接功能实现说明

**实现日期**: 2026-08-11
**功能概述**: 在 Web 界面增加云台手动连接功能，支持自动连接失败后用户手动输入 IP 连接

---

## 一、功能说明

### 1.1 工作流程

1. **自动连接**: 服务启动时，如果 manifest 配置了 `gimbal_host`，自动尝试连接
2. **状态检测**: 前端每 10 秒轮询 `/api/v1/gimbal/state` 检查云台连接状态
3. **手动连接**: 如果自动连接失败，用户可以看到"云台未连接"状态，点击"手动连接云台"按钮
4. **IP 输入**: 弹出模态框，用户输入云台 IP 地址、用户名、密码
5. **连接验证**: 后端验证 IP 格式，尝试连接云台
6. **更新配置**: 连接成功后，更新服务端的云台适配器，并同步 RTSP 地址到视频管理器

### 1.2 默认配置

- 默认 IP: `192.168.1.108`（文档示例地址）
- 默认用户名: `admin`
- 默认密码: `123456`（云台文档规定）

---

## 二、后端实现

### 2.1 新增 API 端点

**POST** `/api/v1/gimbal/connect`

请求体:
```json
{
  "host": "192.168.1.108",
  "username": "admin",
  "password": "123456"
}
```

响应（成功）:
```json
{
  "success": true,
  "host": "192.168.1.108",
  "message": "云台连接成功",
  "video_urls": {
    "visible_light": "rtsp://192.168.1.108:554/id=1&type=0",
    "thermal": "rtsp://192.168.1.108:554/id=2&type=0"
  }
}
```

响应（失败）:
```json
{
  "success": false,
  "message": "云台连接失败: 192.168.1.108，请检查 IP 和凭据"
}
```

### 2.2 修改文件

| 文件 | 修改内容 |
|------|----------|
| `backend/app/api/extended_handlers.py` | 新增 `GimbalConnectHandler` 类 |
| `backend/app/api/router.py` | 注册 `/api/v1/gimbal/connect` 路由 |
| `backend/app/server.py` | 添加 `gimbal_connected` 和 `gimbal_host` 属性 |

---

## 三、前端实现

### 3.1 新增 UI 元素

1. **云台状态面板**: 显示连接状态和 IP 地址
2. **手动连接按钮**: 点击弹出连接模态框
3. **扫描云台按钮**: 返回已配置地址，方便用户快速填充
4. **连接模态框**: 包含 IP、用户名、密码输入框

### 3.2 JavaScript 函数

| 函数 | 功能 |
|------|------|
| `updateGimbalStatus(connected, host)` | 更新云台状态显示 |
| `showGimbalModal()` | 显示连接模态框 |
| `hideGimbalModal()` | 隐藏连接模态框 |
| `connectGimbal()` | 发送连接请求 |
| `scanGimbal()` | 获取已配置地址并填充表单 |

### 3.3 轮询机制

- 每 10 秒轮询 `/api/v1/gimbal/state`
- 连接成功后自动刷新视频状态

---

## 四、使用说明

### 4.1 自动连接（推荐）

在 `deploy/readonly-manifest.json` 中配置云台地址：

```json
{
  "targets": {
    "gimbal_host": "192.168.1.108",
    "gimbal_username": "admin",
    "gimbal_password": "123456"
  }
}
```

### 4.2 手动连接

1. 登录 Web 界面
2. 在顶部看到"云台未连接"状态
3. 点击"手动连接云台"按钮
4. 输入云台 IP 地址（默认 192.168.1.108）
5. 确认用户名和密码（默认 admin/123456）
6. 点击"连接"按钮
7. 连接成功后，状态变为"云台已连接 192.168.1.108"
8. 视频流状态自动刷新

### 4.3 扫描云台

1. 点击"扫描云台"按钮
2. 系统返回 manifest 中配置的地址
3. 自动填充到模态框
4. 用户确认后点击"连接"

---

## 五、技术细节

### 5.1 云台协议

- 协议: Soar Security WEB2.0
- 端口: 80 (HTTP), 554 (RTSP)
- 认证: Basic Auth (base64)
- 视频流:
  - 可见光: `rtsp://{host}:554/id=1&type=0`
  - 热成像: `rtsp://{host}:554/id=2&type=0`

### 5.2 错误处理

| 错误 | 原因 | 处理 |
|------|------|------|
| IP 格式错误 | 输入非 IP 地址 | 前端验证，返回 400 |
| 连接超时 | 网络不通或 IP 错误 | 返回 503 |
| 认证失败 | 用户名或密码错误 | 返回 503 |
| 服务未启动 | 后端服务未运行 | 前端显示请求失败 |

### 5.3 安全考虑

- 连接操作需要管理员权限
- 密码不回显到前端状态
- IP 地址验证防止注入攻击

---

## 六、测试验证

### 6.1 单元测试

```bash
# 编译检查
python3 -m compileall -q backend/

# 导入检查
python3 -c "from backend.app.api.extended_handlers import GimbalConnectHandler"
```

### 6.2 集成测试

1. 启动服务: `python3 -m backend.app.server --manifest deploy/readonly-manifest.json`
2. 登录 Web 界面
3. 检查云台状态面板显示
4. 点击"手动连接云台"
5. 输入正确的云台 IP 和凭据
6. 验证连接成功后状态变化
7. 验证视频流状态更新

---

## 七、后续改进建议

1. **自动发现**: 实现网络扫描功能，自动发现云台设备
2. **连接持久化**: 将手动连接的 IP 保存到配置文件
3. **多云台支持**: 支持同时连接多个云台
4. **连接测试**: 在提交前测试网络连通性
5. **日志记录**: 记录连接尝试和成功/失败日志

---

**实现人**: Hermes Agent
**文档版本**: V1.0
