# M20 Pro 巡逻机器人系统

基于山猫 M20 Pro 机器狗的安保巡逻监控系统，部署于 GOS 边缘计算主机。

**机型**: 山猫 M20 Pro  
**部署位置**: GOS 主机（10.21.31.104）  
**状态**: 开发阶段，待实机验证

---

## 系统架构

```
┌──────────────┐     HTTP/WebSocket     ┌─────────────────┐
│  Web Browser │◄──────────────────────►│   GOS 主机      │
│  :8080       │                        │  (10.21.31.104) │
└──────────────┘                        └───────┬─────────┘
                                                │ TCP 30001
                                        ┌───────▼─────────┐
                                        │   AOS 主机      │
                                        │  (10.21.31.103) │
                                        │  M20 Pro 机器狗 │
                                        └─────────────────┘
```

**数据流**: AOS 主动推送 Type=1002/1007 状态消息 → basic_server 客户端解析 → WebSocket/REST API → 前端展示

---

## 快速开始

### 本地开发调试

```bash
cd ~/m20-patrol-robot
bash deploy/scripts/start.sh
```

访问 `http://127.0.0.1:8080`

### 生产部署（GOS 主机）

```bash
# 一键部署
bash deploy/scripts/deploy-readonly.sh --one-shot

# 健康检查
curl http://127.0.0.1:8080/api/v1/health

# 查看状态
curl http://127.0.0.1:8080/api/v1/status/latest
```

### 回滚

```bash
bash deploy/scripts/rollback-gos.sh
```

---

## 功能清单

| 模块 | 功能 | 协议 | 状态 |
|------|------|------|------|
| 状态监控 | 位置、电量、运动状态实时显示 | Type=1002/1007 | ✅ 已实现 |
| 视频回传 | 四路视频（前/后广角+热成像+云台） | RTSP 8554 | ✅ 已实现 |
| 运动控制 | 前进/后退/转向/急停/回充 | Type=2 Cmd=21/22/24 | ✅ 已实现 |
| 导航管理 | 单点导航、任务下发与取消 | Type=1003/1004/1007 | ✅ 已实现 |
| 云台控制 | 方向调节、变倍、激光测距 | 数尔WEB协议 | ✅ 已实现 |
| 异常告警 | 错误码解析、工单管理 | Type=1002 Cmd=3 | ✅ 已实现 |
| 认证鉴权 | 用户登录、会话管理 | 内置 | ✅ 已实现 |
| 巡检管理 | 巡检点配置、覆盖率统计 | 自定义 | ✅ 已实现 |

---

## 端口配置

| 端口 | 服务 | 用途 |
|------|------|------|
| 8080 | Web服务 | HTTP API + 静态文件 |
| 30001 | AOS TCP | basic_server 状态订阅+控制 |
| 8554 | RTSP | 视频流 |
| 80 | 云台HTTP | 云台控制API |

---

## 配置说明

### 运行时配置

编辑 `deploy/readonly-manifest.json`：

```json
{
  "runtime_mode": "realtime",        // 运行时模式
  "read_only_mode": false,            // 只读模式（true=禁止控制）
  "control_enabled": true,            // 控制权限开关
  "telemetry_tx_enabled": true,       // 心跳发送（必须为true）
  "auth_enabled": false,              // 认证开关
  "allow_anonymous": true,            // 匿名访问
  "static_root": "web"                // Web UI目录
}
```

### 目标主机配置

```json
{
  "targets": {
    "gos_host": "10.21.31.104",       // GOS主机（本机）
    "aos_host": "10.21.31.103",       // AOS主机（机器狗）
    "nos_host": "10.21.31.106",       // NOS主机（导航）
    "gimbal_host": "10.21.31.108"     // 云台主机
  }
}
```

---

## 项目结构

```
m20-patrol-robot/
├── backend/                 # 后端代码
│   └── app/
│       ├── server.py        # 服务入口
│       ├── config.py        # 配置加载
│       ├── protocol/        # APDU协议解析
│       ├── robot/           # basic_server客户端
│       ├── api/             # REST API
│       ├── motion/          # 运动控制
│       ├── navigation/      # 导航管理
│       ├── gimbal/          # 云台控制
│       ├── video/           # 视频流管理
│       └── auth/            # 认证鉴权
├── web/                     # Web UI（独立目录）
│   ├── index.html
│   ├── css/
│   └── js/
├── deploy/                  # 部署配置
│   ├── scripts/             # 部署脚本
│   ├── systemd/             # systemd服务文件
│   └── readonly-manifest.json  # 运行配置
├── docs/                    # 文档
│   ├── 项目文档/            # 项目技术文档
│   └── 官方文档/            # 厂商手册
├── var/                     # 运行时数据（SQLite等）
└── archive/                 # 归档（离线部署包等）
```

---

## 故障排查

### 无数据（NO_DATA）

```bash
# 检查TCP连接
timeout 5 bash -c 'echo | nc -v 10.21.31.103 30001'

# 检查心跳配置
grep telemetry_tx_enabled deploy/readonly-manifest.json

# 运行全链路诊断
python3 deploy/scripts/diagnose-full-chain.py
```

### 服务异常

```bash
# 查看服务状态
systemctl --user status m20-patrol-readonly.service

# 查看日志
journalctl --user -u m20-patrol-readonly.service -n 50 --no-pager -l
```

详细排查见 [故障排查手册](./docs/项目文档/05-故障排查手册.md)

---

## 文档索引

| 编号 | 文档 | 读者 |
|------|------|------|
| 00 | [文档索引](./docs/项目文档/00-文档索引.md) | 所有读者 |
| 01 | [项目概述与需求](./docs/项目文档/01-项目概述与需求.md) | 项目负责人 |
| 02 | [系统架构与协议](./docs/项目文档/02-系统架构与协议.md) | 架构师、开发 |
| 03 | [核心模块实现](./docs/项目文档/03-核心模块实现.md) | 后端开发 |
| 04 | [部署与运维指南](./docs/项目文档/04-部署与运维指南.md) | 部署工程师 |
| 05 | [故障排查手册](./docs/项目文档/05-故障排查手册.md) | 运维支持 |
| 06 | [API参考](./docs/项目文档/06-API参考.md) | 前端开发 |
| 07 | [协议对齐说明](./docs/项目文档/07-协议对齐说明.md) | 技术负责人 |
| 08 | [功能演示方案](./docs/项目文档/08-功能演示方案.md) | 演示人员 |

### 官方文档

- [山猫M20软件开发指南V1.2.1](./docs/官方文档/机器狗本体/山猫M20软件开发指南V1.2.1.md) — 核心协议规范
- [山猫M20basic_server通信协议总览](./docs/官方文档/机器狗本体/山猫M20basic_server通信协议总览.md) — APDU格式详解
- [数尔WEB通讯协议V1.0](./docs/官方文档/上装设备/数尔WEB通讯协议V1.0.md) — 云台控制协议

---

## 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| 后端语言 | Python | 3.8.10 |
| 网络框架 | http.server（标准库） | 无第三方依赖 |
| 数据库 | SQLite | 内置 |
| 视频处理 | FFmpeg | 7.1+ |
| 前端框架 | 原生JS | 无构建依赖 |
| 协议格式 | JSON | basic_server官方支持 |

---

## 安全特性

1. **三级权限控制**: read_only_mode → control_enabled → auth_required
2. **安全快照检查**: 运动控制前验证状态、电量、急停
3. **审计日志**: 所有控制操作记录操作人和时间
4. **系统隔离**: systemd服务限制权限（PrivateTmp、ProtectSystem）

---

## 许可

MIT License - 详见 [LICENSE](./LICENSE)

---

*本系统基于《山猫M20软件开发指南V1.2.1》开发*
