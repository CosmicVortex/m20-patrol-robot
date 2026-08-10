# M20 Pro 巡逻机器人代码审查报告

审查日期: 2026-08-10  
审查范围: backend/app/ 下所有 .py 文件，deploy/scripts/ 下 shell 脚本  
测试状态: 180 tests pass

---

## P0 - 严重问题（运行时错误/崩溃）

### P0-1: 云台处理器调用不存在的 `read_json_body()` 方法
- **位置**: `backend/app/gimbal/handlers.py:45,64,90`
- **描述**: `GimbalMoveHandler`、`GimbalZoomHandler`、`GimbalAngleHandler` 的 `do_POST` 方法调用 `self.read_json_body()`，但 `BaseGimbalHandler` 继承自 `ApiFormatter` 而非 `BaseHandler`。路由分派时传入的是 `M20RequestHandler`（BaseHTTPRequestHandler 实例），该类只有 `_parse_json_body()` 方法，没有 `read_json_body()`。
- **影响**: 所有云台控制 API（/api/v1/gimbal/move、/gimbal/zoom、/gimbal/angle）在调用时会抛出 `AttributeError`，导致 500 错误。
- **修复建议**: 将 `self.read_json_body()` 替换为 `self._parse_json_body()`（M20RequestHandler 继承自 BaseHandler，该方法可用）。

### P0-2: 云台处理器缺少 HTTP Handler 属性
- **位置**: `backend/app/gimbal/handlers.py`（整个文件）
- **描述**: 所有 `Gimbal*Handler` 类继承自 `ApiFormatter`，不包含 `BaseHTTPRequestHandler`。路由通过 `getattr(handler_class, handler_method)(handler)` 调用，传入的是 `M20RequestHandler` 实例。`BaseGimbalHandler._get_gimbal()` 使用 `getattr(self, '_gimbal', None)` 可正常工作，但 `send_json_response` 和 `send_error_response` 方法在 `ApiFormatter` 中不存在（只有静态方法 `send_json`/`send_error`）。
- **影响**: 云台处理器调用 `self.send_json_response()` 时会报 `AttributeError`。
- **修复建议**: 
  1. 让 `BaseGimbalHandler` 继承 `BaseHandler`，或
  2. 在 `BaseGimbalHandler` 中添加 `send_json_response` 和 `send_error_response` 方法，或
  3. 将调用改为 `ApiFormatter.send_json(self, 200, data)` 等静态方法调用。

### P0-3: 健康检查表达式三元运算符优先级陷阱
- **位置**: `backend/app/api/handlers.py:126`
- **描述**: `health["healthy"]` 的最后一项是 `0 <= age_ms < X if telemetry_adapter else False`。Python 三元运算符优先级低于 `<`，实际解析为 `(all_previous_ands) and (0 <= age_ms < X if telemetry_adapter else False)`。当 `telemetry_adapter` 为 None 时返回 False，健康检查失败。
- **影响**: 在 `telemetry_adapter` 为 None 时健康检查返回 503（即使其他条件满足）。当前代码中 `setup()` 总是创建 `telemetry_adapter`，所以不会触发，但这是一个隐蔽的 bug 种子。
- **修复建议**: 添加括号明确优先级: `(0 <= health["age_ms"] < (self.telemetry_adapter.config.stale_after_s * 1000 if self.telemetry_adapter else 0))`

---

## P1 - 高优先级问题

### P1-1: 默认密码硬编码在部署脚本中
- **位置**: `deploy/scripts/deploy-readonly.sh:58-59`
- **描述**: 脚本在首次部署时自动创建 `passwords.env` 文件，其中 `M20_GIMBAL_PASSWORD` 和 `M20_ADMIN_PASSWORD` 默认值均为 `123456`。虽然 `config.py` 中有警告日志，但脚本无条件创建包含默认密码的文件。
- **影响**: 新部署的机器人默认使用弱密码，存在安全风险。密码文件权限为 600，但内容仍可见。
- **修复建议**: 移除脚本中的默认密码创建逻辑，改为要求用户通过环境变量或交互方式提供密码。如果文件已存在则不覆盖。

### P1-2: install-gos.sh 错误时未清理 release 目录
- **位置**: `deploy/scripts/install-gos.sh:216-339`
- **描述**: 在第 216 行验证失败时，脚本调用 `rm -rf "$RELEASE"` 并 `exit 1`，绕过了 trap cleanup 处理器。在第 336 行的 service state 检查失败时，同样直接 `exit 0`，未清理已创建的 release 目录。
- **影响**: 失败部署后遗留不完整的 release 目录，可能占用磁盘空间并导致后续部署混淆。
- **修复建议**: 确保所有错误路径都通过 cleanup trap 或显式清理 release 目录。

### P1-3: install-gos.sh 临时 unit 文件未清理
- **位置**: `deploy/scripts/install-gos.sh:323-334`
- **描述**: 在第 323 行创建 `UNIT_TMP` 临时文件，第 334 行调用 `chmod 600`，第 340 行 `mv -f` 到最终位置。如果 mv 失败或后续操作失败，临时文件未被清理。
- **影响**: 临时文件残留，可能暴露 systemd unit 内容。
- **修复建议**: 在 trap cleanup 中加入 `rm -f "${UNIT_TMP:-}"`（已有，但需确认执行路径）。

### P1-4: 密码环境变量空字符串问题
- **位置**: `backend/app/config.py:95`
- **描述**: `os.environ.get("M20_GIMBAL_PASSWORD") or data.get("gimbal_password", "123456")` — 如果环境变量存在但为空字符串，`or` 会回退到默认值。但如果显式设置为空字符串，可能导致认证问题。
- **影响**: 配置行为不符合预期，用户可能误以为设置了密码。
- **修复建议**: 改为 `os.environ.get("M20_GIMBAL_PASSWORD") if os.environ.get("M20_GIMBAL_PASSWORD") else data.get("gimbal_password", "123456")`

### P1-5: auth/store.py 过度使用 assert
- **位置**: `backend/app/auth/store.py:151`
- **描述**: `assert row is not None` 在已经检查过 row 可能为 None 的情况下。Python 的 assert 可以被 `-O` 标志禁用，导致生产环境中静默失败。
- **影响**: 如果 assert 被禁用且 row 为 None，后续 `self._row_to_user(row)` 会抛出 AttributeError 而非有意义的错误。
- **修复建议**: 用 `if row is None: raise AuthenticationError(...)` 替代 assert。

### P1-6: auth/middleware.py 重复的 anonymous 检查
- **位置**: `backend/app/auth/middleware.py:101-108`
- **描述**: 第 101 行检查 `self.allow_anonymous` 并返回 None，第 106 行再次检查 `self.allow_anonymous`。虽然功能正确，但逻辑冗余且容易误导。
- **影响**: 代码可读性降低，维护时可能引入 bug。
- **修复建议**: 移除第 106-107 行的冗余检查。

### P1-7: f-string 日志表达式（非致命但影响性能）
- **位置**: `backend/app/navigation/service.py:74,118`
- **描述**: 使用 `logger.info(f"Navigation authorized by {operator}")` 而非 `logger.info("Navigation authorized by %s", operator)`。f-string 在日志级别过滤前就求值。
- **影响**: 在 DEBUG 级别关闭时仍会创建字符串对象，轻微性能影响。
- **修复建议**: 使用标准日志格式化: `logger.info("Navigation authorized by %s", operator)`

---

## P2 - 中等优先级问题

### P2-1: telemetry_tx_enabled 条件永远为 False
- **位置**: `backend/app/robot/telemetry.py:184`
- **描述**: `if self.config.telemetry_tx_enabled:` 条件在运行时永远不会为 True，因为 `ConnectionConfig.__post_init__` 在第 56 行强制抛出 ValueError。
- **影响**: 第 185-190 行的心跳发送逻辑是死代码，但无害。
- **修复建议**: 移除死代码或添加注释说明有意为之。

### P2-2: 硬编码的 NOS 主机地址
- **位置**: `backend/app/api/handlers.py:257`
- **描述**: `DevicesListHandler` 中硬编码了 `{"id": "nos", "type": "navigation_operator_station", "host": "10.21.31.106", ...}`。
- **影响**: 如果实际部署中 NOS 地址不同，API 返回错误信息。
- **修复建议**: 从配置中读取 NOS 地址，或使用 `self.config` 中的值。

### P2-3: video_manager 类型不一致
- **位置**: `backend/app/server.py:52`
- **描述**: `self.video_manager = None` 没有类型注解，而其他属性使用 `Optional[Type] = None`。
- **影响**: 类型检查器可能发出警告，代码一致性差。
- **修复建议**: 改为 `self.video_manager: Optional[VideoStreamManager] = None`

### P2-4: 路由中冗余的 hasattr 检查
- **位置**: `backend/app/server.py:245-248`
- **描述**: 路由器已经在 `__init__` 中设置了 `self.gimbal_adapter` 和 `self.video_manager`，但请求处理中仍使用 `hasattr` 检查。
- **影响**: 代码冗余，不必要地增加了复杂性。
- **修复建议**: 移除 hasattr 检查，直接使用 `self._gimbal = router.gimbal_adapter`。

### P2-5: 导航服务未使用安全快照更新
- **位置**: `backend/app/server.py:91-104`
- **描述**: 创建 `NavigationSafetySnapshot` 后，`control_enabled` 固定为 `config.control_enabled`（始终为 False）。虽然 `NavigationService.send_navigation` 会检查此标志并返回错误，但快照值从未更新。
- **影响**: 如果将来需要动态更新安全状态，当前实现不支持。
- **修复建议**: 添加更新安全快照的方法，或在需要时从遥测数据更新快照。

### P2-6: 缺少速率限制
- **位置**: `backend/app/auth/middleware.py`、`backend/app/api/handlers.py`
- **描述**: 认证端点（login）和云台控制端点没有速率限制。
- **影响**: 暴力破解或滥用风险。
- **修复建议**: 添加简单的速率限制中间件，限制每分钟尝试次数。

### P2-7: 缺少安全响应头
- **位置**: `backend/app/api/handlers.py`
- **描述**: 响应中设置了 `X-Content-Type-Options: nosniff` 和 `Cache-Control: no-store`，但缺少 `X-Frame-Options`、`Content-Security-Policy` 等。
- **影响**: 潜在的点击劫持和 XSS 风险。
- **修复建议**: 添加 `X-Frame-Options: DENY` 和基本的 CSP 头。

### P2-8: 日志中泄露敏感信息
- **位置**: `deploy/scripts/deploy-readonly.sh:98-99`
- **描述**: `show-passwords` 命令和 `preflight` 函数会打印密码值到 stdout。
- **影响**: 密码可能出现在终端历史、日志文件或屏幕截图中。
- **修复建议**: 移除密码打印功能，或使用 `***` 掩码显示。

---

## 总结

| 级别 | 数量 | 关键问题 |
|------|------|----------|
| P0 | 3 | 云台处理器方法不存在、健康检查表达式 |
| P1 | 7 | 默认密码、脚本清理、配置回退 |
| P2 | 8 | 死代码、硬编码值、缺少安全头 |

**最高优先级修复**: P0-1 和 P0-2（云台处理器运行时崩溃）必须在部署前修复。
