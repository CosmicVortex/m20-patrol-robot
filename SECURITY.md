# 安全策略

> 本文档说明 M20 Pro 巡逻机器人系统的安全机制与最佳实践。

---

## 认证与授权

### 用户认证

- 所有控制接口需登录后访问（`/api/v1/auth/login`）
- 会话通过 `session_id` Cookie 管理
- 支持多用户并发会话

### 控制权限模型

| 操作类型 | 权限要求 |
|---------|----------|
| 状态查询 | 无需认证（自动登录模式已启用） |
| 视频获取 | 无需认证 |
| 运动控制 | 需授权（Web UI 显式点击"授权运动控制"） |
| 导航控制 | 需授权（Web UI 显式点击"授权导航控制"） |
| 用户管理 | 仅 admin 角色可操作 |

### 安全快照机制

每次控制指令执行前，系统会检查：

1. **读只模式**：`read_only_mode: true` 时禁止所有控制
2. **授权状态**：运动/导航需单独授权
3. **急停状态**：机器狗处于软急停时拒绝运动指令
4. **电量阈值**：电量过低时限制运动控制

---

## 数据安全

### 本地存储

- 用户凭据存储在 SQLite 数据库（`backend/app/data/m20_auth.db`）
- 密码使用 PBKDF2-HMAC-SHA256 哈希存储，盐值随机生成
- 工单数据存储在 `backend/app/data/work_orders.jsonl`

### 网络传输

- Web 服务仅监听内网（10.21.31.0/24）
- basic_server 协议为纯文本 JSON，传输无加密
- 建议在生产环境中使用 VPN 隔离网络

---

## 配置安全

### Manifest 配置

部署配置通过 `deploy/readonly-manifest.json` 管理：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `auth_enabled` | false | 认证中间件开关 |
| `allow_anonymous` | true | 允许匿名访问（测试模式） |
| `read_only_mode` | true | 只读模式（禁止控制） |
| `control_enabled` | false | 控制功能总开关 |

### 密码管理

**本地测试密码文件**：`~/.config/m20-patrol/passwords.env`

```bash
# AOS 访问密码
AOS_PASSWORD=<your_password>

# 云台访问密码（数尔WEB协议）
GIMBAL_PASSWORD=<your_password>
```

> **注意**：生产部署后务必修改默认密码。云台密码通过 `/api/v1/gimbal/connect` 接口设置。

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 未授权控制 | 机器狗意外运动 | read_only_mode + 授权机制双重保护 |
| 网络暴露 | 外部访问内网设备 | 10.21.31.0/24 私有网络隔离 |
| 凭据泄露 | 非授权用户操作 | SQLite + PBKDF2 哈希存储 |
| 数据篡改 | 工单/配置被修改 | 部署包完整性校验 |

---

## 安全审计

### 本地环境

- 当前为本地开发/演示环境，`auth_enabled: false`
- 所有接口默认可访问，无需登录

### 生产环境建议

1. 启用 `auth_enabled: true`
2. 设置强密码（不少于8位，含大小写字母和数字）
3. 关闭 `allow_anonymous`
4. 仅在内网环境使用
5. 定期备份 `m20_auth.db` 和 `work_orders.jsonl`

---

**文档版本**: V1.0  
**最后更新**: 2026-08-16
