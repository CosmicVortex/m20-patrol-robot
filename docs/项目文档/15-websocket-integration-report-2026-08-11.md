# M20 Pro 巡逻机器人 - WebSocket 集成报告

**完成日期**: 2026-08-11  
**状态**: ✅ 完成  
**测试**: 181 passed

---

## 一、WebSocket 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (index.html)                   │
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │ WebSocket    │      │ WebSocket    │                    │
│  │ /ws/video    │      │ /ws/nav      │                    │
│  │ (video_states)│     │ (nav_ctrl)   │                    │
│  └──────┬───────┘      └──────┬───────┘                    │
│         │                     │                             │
│         └──────────┬──────────┘                             │
│                    ▼                                        │
│           WebSocket Manager (JS)                           │
│           - Auto reconnect (3s)                            │
│           - Message routing                                │
│           - State sync                                     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              M20WebServer (backend/app/server.py)            │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              WebSocketUpgradeHandler                  │  │
│  │  - HTTP upgrade handshake                           │  │
│  │  - Frame parsing                                     │  │
│  │  - Client connection management                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                │
│         ┌─────────────────┼─────────────────┐              │
│         ▼                 ▼                 ▼              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │VideoWS      │  │NavWS        │  │Frame IO     │       │
│  │Handler      │  │Handler      │  │(TCP)        │       │
│  │- get_states │  │- authorize  │  │             │       │
│  │- select     │  │- deauthorize│  │             │       │
│  │- get_selected│  │- send_nav  │  │             │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、后端实现

### 2.1 新增文件

#### `backend/app/websocket/ws_handler.py`
```python
class WebSocketHandler:
    """Base WebSocket handler with auth and routing."""
    def on(self, action: str, handler: Any) -> None
    async def handle_message(self, message: str) -> Optional[dict]

class VideoWebSocketHandler(WebSocketHandler):
    """Handle video stream WebSocket connections."""
    Actions:
    - get_states: 获取所有摄像头状态
    - select_stream: 选择视频源
    - get_selected: 获取当前选中源

class NavigationWebSocketHandler(WebSocketHandler):
    """Handle navigation WebSocket messages."""
    Actions:
    - authorize: 授权导航控制
    - deauthorize: 撤销授权
    - send_navigation: 发送导航命令
    - cancel_navigation: 取消导航
    - get_status: 获取导航状态
    - get_audit_log: 获取操作日志
```

#### `backend/app/websocket/upgrade.py`
```python
class WebSocketUpgradeHandler:
    """Handles WebSocket upgrade requests in the main HTTP server."""
    
    Methods:
    - handle_request(conn): 处理 WebSocket 升级请求
    - _read_frame(conn): 读取 WebSocket 帧
    - _send_text(conn, data): 发送文本帧
    - _get_handler(path): 根据路径选择处理器
```

### 2.2 修改文件

#### `backend/app/server.py`
```python
# 新增导入
from backend.app.websocket.ws_handler import (
    init_ws_handlers, 
    video_ws_handler, 
    navigation_ws_handler
)
from backend.app.websocket.upgrade import WebSocketUpgradeHandler

# 新增属性
self.ws_upgrade_handler: Optional[WebSocketUpgradeHandler] = None

# setup() 方法中初始化
if self.video_manager and self.nav_service:
    init_ws_handlers(self.video_manager, self.nav_service)
    self.ws_upgrade_handler = WebSocketUpgradeHandler(
        video_handler=video_ws_handler,
        nav_handler=navigation_ws_handler,
    )

# _create_handler() 中处理升级
if router:
    upgrade_header = self.headers.get("Upgrade", "").lower()
    if upgrade_header == "websocket":
        if server_instance and server_instance.ws_upgrade_handler:
            sock = self.request
            server_instance.ws_upgrade_handler.handle_request(sock)
            return
```

---

## 三、前端实现

### 3.1 新增 JavaScript 函数

```javascript
// WebSocket 连接管理
let wsVideo = null;
let wsNav = null;
let wsReconnectTimer = null;

// 构建 WebSocket URL
function getWsUrl(path) {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${location.host}${path}`;
}

// 连接视频 WebSocket
function connectVideoWebSocket() {
  // 建立 /ws/video 连接
  // 监听 video_states 消息
  // 自动重连（3秒）
}

// 连接导航 WebSocket
function connectNavWebSocket() {
  // 建立 /ws/navigation 连接
  // 监听导航控制消息
  // 自动重连（3秒）
}

// 发送视频消息
function sendWsVideo(action, params = {}) {
  // action: "get_states", "select_stream", "get_selected"
}

// 发送导航消息
function sendWsNav(action, params = {}) {
  // action: "authorize", "send_navigation", "cancel_navigation", etc.
}

// 初始化 WebSocket（登录后调用）
function initWebSocket() {
  connectVideoWebSocket();
  connectNavWebSocket();
}
```

### 3.2 集成点

1. **登录成功后**: `initWebSocket()` 在 `handleLogin()` 中调用
2. **实时状态推送**: WebSocket 连接后自动推送视频状态

---

## 四、WebSocket 协议

### 4.1 消息格式

所有消息使用 JSON 格式：

```json
// 客户端 → 服务器
{
  "action": "get_states",
  // ... 其他参数
}

// 服务器 → 客户端
{
  "type": "video_states",
  "data": {
    "front": { "state": "connected", "url": "rtsp://..." },
    "rear": { "state": "disconnected" },
    "thermal": { "state": "blocked" }
  }
}
```

### 4.2 视频 WebSocket (`/ws/video`)

| Action | 参数 | 返回类型 | 说明 |
|--------|------|----------|------|
| `get_states` | - | `video_states` | 获取所有摄像头状态 |
| `select_stream` | `source` | `video_selected` | 选择视频源 |
| `get_selected` | - | `video_selected` | 获取当前选中源 |

### 4.3 导航 WebSocket (`/ws/navigation`)

| Action | 参数 | 返回类型 | 说明 |
|--------|------|----------|------|
| `authorize` | `operator`, `note` | `authorized` | 授权导航控制 |
| `deauthorize` | - | `deauthorized` | 撤销授权 |
| `send_navigation` | `pos_x`, `pos_y`, `pos_z`, `angle_yaw`, `map_id` | `sent`/`error` | 发送导航命令 |
| `cancel_navigation` | - | `cancelled`/`error` | 取消导航 |
| `get_status` | - | `status` | 获取导航服务状态 |
| `get_audit_log` | - | `audit_log` | 获取操作日志 |

---

## 五、安全特性

1. **认证保护**: WebSocket 连接需要有效的 HTTP Session Cookie
2. **授权检查**: 导航控制需要明确的 Web UI 授权（`field_authorization`）
3. **连接隔离**: 每个 WebSocket 连接独立处理，互不影响
4. **优雅关闭**: 客户端断开时自动清理资源

---

## 六、测试结果

```bash
$ uv run --with pytest python3 -m pytest backend/tests/ -q
181 passed in 5.46s
```

---

## 七、部署验证清单

- [ ] 启动服务器: `python3 backend/app/server.py --manifest deploy/readonly-manifest.json`
- [ ] 浏览器访问: `http://10.21.31.104:8080/`
- [ ] 登录成功后检查控制台: `Video WS connected`, `Navigation WS connected`
- [ ] 测试视频状态推送: 打开浏览器 DevTools → Network → WS
- [ ] 测试导航授权: 点击仪表盘上的"授权控制"按钮
- [ ] 测试视频选择: 切换摄像头源

---

## 八、后续优化建议

1. **心跳机制**: 添加 WebSocket 心跳保持连接
2. **二进制帧**: 支持视频帧直接传输（而非 RTSP URL）
3. **压缩**: 启用 permessage-deflate 压缩
4. **限流**: 添加消息频率限制防止滥用
5. **监控**: 添加 WebSocket 连接数监控指标

---

**报告完成时间**: 2026-08-11 15:00  
**修复人员**: Hermes Agent  
**测试环境**: Python 3.13.5, pytest 9.1.1
