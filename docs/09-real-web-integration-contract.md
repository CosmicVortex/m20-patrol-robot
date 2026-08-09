# 09 — 真实Web集成契约

**目标**：将演示页面升级为真实Web应用，所有能力必须显示 `UNVERIFIED` 或 `BLOCKED`，不得伪造在线状态。

## 已确认事实

| 能力 | 状态 | 文件 |
|------|------|------|
| APDU/ASDU编解码 | ✅ | `protocol/frame.py` |
| 状态消息解析 | ✅ | `robot/status.py` |
| TCP状态订阅 | ✅ | `robot/telemetry.py` |
| 导航报文构造 | ✅ | `navigation/v010.py` |
| Web服务入口 | ✅ | `server.py` |
| 认证模块 | ✅ | `auth/middleware.py` |
| 部署脚本 | ✅ | `deploy/scripts/` |
| 视频管理器 | 🟡 | `video/`（地址待实测） |
| 运动控制 | 🔴 | 代码未实现 |
| 多点巡逻 | 🔴 | 待R-08验收后 |
| 云台适配 | 🔴 | 待实物确认 |

## 开发顺序

1. API骨架 + 认证 + 审计（已完成）
2. 真实遥测接入 + 前端替换
3. 视频探测、转码、截图、录像
4. 导航状态查询 + 授权流程
5. 导航下发/取消（需现场授权）
6. 运动控制（逐项放行）
7. 前端完整数据绑定

## 状态定义

- `implemented` — 代码存在
- `offline_verified` — 离线测试通过
- `runtime_integrated` — 待现场连接
- `field_verified` — 待现场验证
- `blocked` — 安全/配置条件不满足

## 当前整体状态

`contract_drafted / code_components_present / offline_verified / real_web_api_not_implemented / control_field_blocked`
