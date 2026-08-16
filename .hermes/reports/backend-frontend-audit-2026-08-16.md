# M20 Pro 后端-前端全面审计报告

**审计时间**: 2026-08-16  
**审计目标**: 诊断部署到GOS后无法看到机器狗实时数据的问题  
**执行者**: Agnes (云端主代理) + 独立子代理审查

---

## 🔴 P0: 根本原因已定位并修复

### 问题描述
部署脚本和systemd服务文件错误地将 `M20_TELEMETRY_TX_ENABLED=false`，导致心跳被禁用。

**官方文档明确要求**（《山猫M20 basic_server通信协议总览.md》§3.1）：
> 无论使用 UDP 或 TCP，客户端均应以不低于 **1Hz** 的频率发送任意指令作为心跳；服务端超过 **2s** 未收到客户端任何请求则认为客户端离线，**停止向该客户端推送所有主动上报数据**。

### 影响
- `telemetry_tx_enabled=false` → 不发送心跳
- AOS 在2秒后停止推送所有状态数据
- 前端始终显示 `NO_DATA`

### 修复内容
| 文件 | 修改前 | 修改后 |
|------|--------|--------|
| `deploy/scripts/deploy-readonly.sh:267` | `M20_TELEMETRY_TX_ENABLED=false` | `M20_TELEMETRY_TX_ENABLED=true` |
| `deploy/systemd/m20-patrol-readonly.service:14` | `M20_TELEMETRY_TX_ENABLED=false` | `M20_TELEMETRY_TX_ENABLED=true` |
| `deploy/systemd/m20-patrol-realtime.service:14` | `M20_TELEMETRY_TX_ENABLED=false` | `M20_TELEMETRY_TX_ENABLED=true` |

---

## ✅ Phase 1: 基础验证

| 检查项 | 结果 | 说明 |
|--------|------|------|
| Python 编译 | ✅ | `compileall` 通过 |
| 模块导入 | ✅ | `M20WebServer` 导入成功 |
| Manifest配置 | ✅ | `runtime_mode=realtime`, `auth_enabled=false` |
| TCP端口配置 | ✅ | `aos_host=10.21.31.103`, `aos_port=30001` |
| 心跳配置 | ✅ (已修复) | `telemetry_tx_enabled=true` |

---

## ✅ Phase 2: 数据流完整性验证

### 后端数据流
```
TCP 30001 (AOS)
    ↓ BasicServerClient.connect()
    ↓ 发送心跳 (Type=100, Cmd=100, 1Hz)
    ↓ 接收状态帧 (Type=1002, Cmd=3/4/5/6)
    ↓ parse_status_message()
    ↓ TelemetryAdapter._process_message()
    ↓ /api/v1/status/latest → JSON payload
```

### 前端数据流
```
/api/v1/status/latest
    ↓ ApiService.fetchStatus()
    ↓ StateManager.updateTelemetry()
    ↓ DashboardView._updateDashboard()
    ↓ DOM 元素更新
```

### 字段映射验证
| 后端字段 | 前端引用 | 状态 |
|----------|----------|------|
| `source` | `robot.source` | ✅ |
| `connected` | `robot.connected` | ✅ |
| `battery_percent` | `robot.battery` | ✅ |
| `data.basic.motion_state` | `robot.motion_state` | ✅ |
| `data.device.battery_list` | `robot.battery_list` | ✅ |

---

## ✅ Phase 3: 官方文档对齐检查

| 检查项 | 官方要求 | 代码实现 | 状态 |
|--------|----------|----------|------|
| APDU 头部 | V1.2.1 §1.1.5 | `protocol/frame.py` | ✅ |
| 心跳频率 | ≥1Hz | `heartbeat_interval_s=1.0` | ✅ |
| 心跳超时 | >2s 断开 | `stale_after_s=3.0` | ✅ |
| 运动状态 | V1.2.1 §1.2.3 | `basic.motion_state` | ✅ |
| 电池数据 | V1.2.1 §1.2.5 | `device.battery_list` | ✅ |
| 错误码 | V1.2.1 §1.3.2 | `status.py:NAV_ERROR_CODES` | ✅ |

---

## ✅ Phase 4: 前端 DOM 完整性

所有 `getElementById` 引用均在 `index.html` 中存在：
- `conn-badge` ✅
- `battery-pct` ✅
- `motion-state` ✅
- `login-error` ✅
- `main-app` ✅

---

## ✅ Phase 5: 认证流程验证

**配置状态**：
- `auth_enabled=false` → 跳过认证中间件
- `allow_anonymous=true` → 允许匿名访问
- `control_enabled=true` → 允许控制操作（测试阶段）

**前端行为**：
- `app.js:223-225` 自动以 admin 账户登录（硬编码）
- 无需用户手动输入密码
- 直接进入系统界面

---

## ⚠️ P1: 已知限制（不影响数据读取）

| 问题 | 位置 | 影响 | 建议 |
|------|------|------|------|
| `total_distance` 未解析 | `status.py:229` | 前端里程始终为0 | 确认官方协议是否有此字段 |
| 运动状态映射语义 | `dashboard.js:201` | MotionState=2显示"行走" | 需业务确认是否符合预期 |
| 云台连接依赖 | `gimbal/adapter.py` | 需独立HTTP连接 | 确保 10.21.31.108:80 可达 |

---

## 📋 部署验证清单

请在 GOS 主机上执行以下命令验证修复：

```bash
# 1. 重新部署
cd ~/m20-patrol-robot
bash deploy/scripts/deploy-readonly.sh --one-shot

# 2. 检查服务状态
systemctl --user status m20-patrol-readonly.service

# 3. 查看日志确认心跳发送
journalctl --user -u m20-patrol-readonly.service -n 50 --no-pager -l | grep -E "心跳|连接|ERROR"

# 4. 健康检查（应返回 healthy: true）
curl -s http://127.0.0.1:8080/api/v1/health | python3 -m json.tool

# 5. 状态检查（应返回 source: REAL）
curl -s http://127.0.0.1:8080/api/v1/status/latest | python3 -m json.tool
```

**期望输出**：
```json
{
  "healthy": true,
  "source": "REAL",
  "connected": true,
  "tcp_connected": true,
  "valid_frames": > 0,
  "bytes_received": > 0
}
```

---

## 📦 已更新文件

| 文件 | 变更 |
|------|------|
| `deploy/scripts/deploy-readonly.sh` | 修复心跳配置 |
| `deploy/systemd/m20-patrol-readonly.service` | 修复心跳配置 |
| `deploy/systemd/m20-patrol-realtime.service` | 修复心跳配置 |

---

## 结论

**根本原因**: 部署脚本错误禁用了心跳发送 (`M20_TELEMETRY_TX_ENABLED=false`)，导致 AOS 在2秒后停止推送数据。

**修复状态**: ✅ 已修复，需重新部署到 GOS。

**预期结果**: 部署后前端应显示 `REAL / CONTROL ON`，电池、姿态、位置等数据实时更新。

---

*审计完成时间: 2026-08-16*  
*下次验证: 部署后执行上述验证命令*
