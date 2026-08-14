# M20 Pro 项目代码审查报告

**审查日期**: 2026-08-14
**审查范围**: /opt/data/m20-patrol-robot/backend
**审查维度**: 门禁顺序、数据一致性、硬编码、死代码、异常处理

---

## P0 — 严重问题（影响安全或功能正确性）

### P0-1: 密码明文存储（研发阶段留用）
- **文件**: `backend/app/auth/store.py` 第95-102行
- **问题**: `_hash_password()` 和 `_verify_password()` 直接明文存储和比较密码，注释标注"研发阶段"但未在部署路径中强制要求切换到PBKDF2
- **影响**: 数据库泄露即导致所有凭据明文暴露
- **修复建议**: 在生产路径强制启用PBKDF2哈希，移除或条件化明文回退

### P0-2: 云台连接默认密码硬编码
- **文件**: `backend/app/api/extended_handlers.py` 第665行
- **问题**: `password = body.get("password", "123456")` — 云台连接API使用硬编码默认密码
- **影响**: 未提供密码时自动使用已知默认密码连接，绕过安全校验
- **修复建议**: 移除默认值，强制要求传入密码；若为空返回400错误

### P0-3: WebSocket控制操作权限绕过
- **文件**: `backend/app/websocket/ws_handler.py` 第97-104行
- **问题**: NavigationWebSocketHandler已拦截WebSocket上的控制操作（authorize/send_navigation等），但这些私有方法（`_authorize`、`_send_navigation`等）仍然存在且可被调用，存在潜在的代码保留风险
- **影响**: 若未来有代码重新注册这些action到`_handlers`，将完全绕过HTTP认证
- **修复建议**: 彻底删除这些未被调用的私有方法，或添加明确的"此代码已废弃，不得重新启用"注释

### P0-4: 导航服务研发模式自动授权
- **文件**: `backend/app/navigation/service.py` 第56行
- **问题**: `self._auth = NavigationAuthorization(authorized=True, authorized_by="dev", ...)` — 导航服务默认处于已授权状态，无需任何Web UI授权即可执行导航控制
- **影响**: 在`control_enabled=true`时，任何已认证用户（甚至匿名用户若allow_anonymous=True）可直接发送导航命令
- **修复建议**: 删除研发模式默认授权，改为严格的初始unauthorized状态；开发/测试环境通过配置标志启用

### P0-5: 运动控制角色检查全部注释掉
- **文件**: `backend/app/motion/handlers.py` 第37-39、73-75、109-111、144-146、178-180、214-216、250-252、301-307、338-340行
- **问题**: 所有运动控制Handler的`auth.role != "admin"`检查均被注释掉，标注"研发阶段"，导致任何认证用户均可执行全部运动控制
- **影响**: 紧急停止、姿态切换、轴控制等安全敏感操作无角色限制
- **修复建议**: 生产部署前必须取消注释role检查，或在config中增加`dev_mode`标志统一控制

---

## P1 — 重要问题（功能缺陷或安全隐患）

### P1-1: 门禁顺序不一致 — 运动控制 vs 导航控制
- **文件**: 
  - `backend/app/motion/handlers.py` 第29行
  - `backend/app/api/handlers.py` 第252、291、315、370、407行
- **问题**: 运动控制先检查`control_enabled or read_only_mode`再认证；导航控制在check read_only_mode后执行认证。两者顺序不一致，且运动控制在`control_enabled=False`时仍允许匿名用户访问（虽然返回403，但经过了auth检查）
- **影响**: 控制端点的授权链不一致，难以审计和维护
- **修复建议**: 统一所有控制端点的顺序：read_only_mode检查 → 认证 → 角色检查 → 业务逻辑

### P1-2: 系统信息接口泄露内部网络拓扑
- **文件**: `backend/app/api/extended_handlers.py` 第408-413行
- **问题**: `SystemInfoHandler`在`allow_anonymous=True`时向匿名请求者返回AOS/NOS/GOS主机IP地址和端口
- **影响**: 未认证用户可获取内部网络结构信息
- **修复建议**: 对anonymous用户过滤敏感的网络配置信息，或要求至少认证

### P1-3: 视频状态接口泄露RTSP URL
- **文件**: `backend/app/api/handlers.py` 第505-522行
- **问题**: `VideoStatusHandler`在未认证（anonymous allowed）时返回硬编码的RTSP地址（`rtsp://10.21.31.103:8554/video1`等）
- **影响**: 网络拓扑和摄像头地址泄露给未认证访问者
- **修复建议**: 在匿名模式下不返回真实RTSP URL，或要求认证

### P1-4: Gimbal连接API接受明文密码参数
- **文件**: `backend/app/api/extended_handlers.py` 第662-665行
- **问题**: `/api/v1/gimbal/connect`接口接受明文password字段，且无传输层加密外的额外保护
- **影响**: 密码在HTTP请求体中明文传输，若TLS未启用则完全暴露
- **修复建议**: 文档明确标注需HTTPS；考虑增加密码复杂度校验和日志脱敏

### P1-5: 健康检查端点无认证要求
- **文件**: `backend/app/api/handlers.py` 第36-81行
- **问题**: `/api/v1/health`端点不经过任何认证检查，直接暴露遥测连接状态、网络状态等运维信息
- **影响**: 未认证用户可探测服务状态和网络连通性
- **修复建议**: 评估health端点的信息敏感度，考虑添加基础认证或仅返回最小状态

### P1-6: WebSocket升级处理缺少TLS依赖确认
- **文件**: `backend/app/websocket/upgrade.py` 第38-116行
- **问题**: 自定义WebSocket实现直接解析HTTP头，若部署在无TLS环境中，session token将在请求头中明文传输
- **影响**: 会话劫持风险
- **修复建议**: 文档明确WS需通过HTTPS升级；或在upgrade handler中添加X-Forwarded-Proto检查

---

## P2 — 次要问题（代码质量、维护性）

### P2-1: RTSP地址硬编码多处
- **文件**: 
  - `backend/app/video/stream_manager.py` 第54-57行
  - `backend/app/api/handlers.py` 第505、512行
- **问题**: 视频流管理器中front/rear/thermal/body_front的RTSP URL硬编码为`rtsp://10.21.31.103:8554/...`
- **影响**: 部署到其他网络环境需修改代码
- **修复建议**: 从manifest配置读取，或使用模板变量替换

### P2-2: 云台默认IP硬编码
- **文件**: `backend/app/gimbal/adapter.py` 第246行
- **问题**: `default_ip = "10.21.31.108"` 作为自动发现失败的备用地址
- **影响**: 不同现场网络可能使用不同IP
- **修复建议**: 移除此硬编码，仅保留网络扫描作为fallback，或在配置中允许设置备用IP

### P2-3: 重复的认证检查模式
- **文件**: 多个handler文件中
- **问题**: `if not auth and (not self.auth_middleware or not self.auth_middleware.allow_anonymous)` 模式重复出现约15次，逻辑冗长
- **影响**: 维护困难，易出错
- **修复建议**: 提取为BaseHandler的辅助方法，如`_require_auth(allow_anonymous=False)`

### P2-4: 异常处理过于宽泛
- **文件**: 多处使用`except Exception as e:`
- **问题**: 广泛的通用异常捕获掩盖了具体错误类型，不利于调试
- **影响**: 故障定位困难
- **修复建议**: 按场景细化异常类型，至少记录异常类别

### P2-5: 测试文件残留硬编码凭据
- **文件**: 
  - `backend/tests/test_server_default_password.py` 第15、23、40行
  - `backend/tests/test_auth_store.py` 第39-40行
  - `backend/tests/test_web_runtime_integration.py` 第101、118行
- **问题**: 测试代码中直接使用明文密码"123456"
- **影响**: 若测试代码泄露，暴露默认凭据
- **修复建议**: 使用环境变量或测试配置隔离，避免硬编码

### P2-6: 文档与代码不一致标记
- **文件**: `backend/app/server.py` 第69行注释"研发阶段默认密码123456（部署后修改）"
- **问题**: 此类"研发阶段"标记若无自动化检查，容易遗留在生产代码中
- **影响**: 安全隐患持久化
- **修复建议**: 添加CI检查，扫描代码中的"研发阶段"/"TODO"标记，强制开发者确认

---

## 统计汇总

| 优先级 | 数量 | 主要影响领域 |
|--------|------|-------------|
| P0     | 5    | 认证安全、权限控制 |
| P1     | 6    | 信息泄露、门禁顺序 |
| P2     | 6    | 代码质量、可维护性 |
| **合计** | **17** | |

---

## 关键发现总结

1. **安全架构问题**: 运动控制和导航控制的角色检查被批量注释，形成大面积权限绕过
2. **研发标记残留**: 多处"研发阶段"注释未清理，包括默认密码、自动授权等
3. **门禁顺序不一致**: 不同控制端点的read_only_mode检查位置不统一
4. **信息泄露**: 匿名访问可获取内部网络拓扑和RTSP地址
5. **密码存储**: 生产环境仍使用明文存储，无哈希保护
