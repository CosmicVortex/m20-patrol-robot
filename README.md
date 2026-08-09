# 山猫 M20 Pro 只读实时观测项目

山猫 M20 Pro 巡逻安防系统的二次开发代码库。本阶段只提供 GOS 上的非控制实时状态观测；通过 basic_server 协议从 AOS 接收状态，不启动导航、巡逻、云台、拍照或其他控制路径。

## 项目身份

- **唯一型号**：山猫 M20 Pro（不使用 PRO/STD 等软件型号枚举）
- **演示阶段场地**：[内部测试场地]
- **目标部署场地**：[客户场地]
- **实施顺序**：[测试场地]先完成建图、状态接入、视频切换、单点导航控制验收；全部通过后，[客户场地]重新建图并单独验收
- **部署主机**：GOS（10.21.31.104，项目负责人确认固定地址）
- **当前阶段**：云端离线基线已完成，GOS 真机部署和真实遥测仍未验证，当前状态为 `BLOCKED`

## 固定目标、端口与配置来源

唯一配置来源是版本化 `deploy/readonly-manifest.json`：

```text
GOS_HOST=10.21.31.104
AOS_HOST=10.21.31.103
NOS_HOST=13.21.31.106
AOS_TCP_PORT=30001
AOS_UDP_PORT=30000
RTSP_PORT=8554
WEB_PORT=8080
M20_RUNTIME_MODE=realtime_readonly
READ_ONLY_MODE=true
CONTROL_ENABLED=false
TELEMETRY_RX_ENABLED=true
TELEMETRY_TX_ENABLED=false
WEB_REALTIME_ENABLED=true
```

现场不需要手工修改 IP、端口或运行开关。主机仍必须满足 Python 3.8.10、项目依赖、用户级 systemd、固定路由和端口条件。已废弃地址 `10.21.31.101` 禁止使用。

## 安全边界与运行模式

- `REAL_RECEIVE_ONLY`：只建立经批准的接收链路，永不发送心跳。
- `REAL_READONLY_WITH_HEARTBEAT`：本 release 不启用；若未来协议证据证明接收必须发送 Type=100/Command=100，必须另行审查和批准。
- `SIMULATED`：仅测试使用，不创建机器人 socket，不得冒充真实状态。
- 建图、导航、巡逻、运动、云台、拍照和控制均不属于本只读 release。

## 当前交付

### 已完成（离线验证）

| 能力 | 状态 | 测试 |
|---|---|---|
| APDU 16字节帧编解码 | ✅ 已实现 | protocol/test_frame.py |
| JSON/XML PatrolDevice 信封 | ✅ 已实现 | protocol/test_messages.py |
| 状态消息解析（1002/3,4,5,6; 1007/1,2,3; 2002/1） | ✅ 已实现 | test_status.py |
| TCP客户端+门禁+message_id关联 | ✅ 已实现 | test_basic_client.py |
| 导航报文构造+安全门控 | ✅ 已实现 | test_navigation_v010.py |
| 视频流管理器（RTSP地址模型） | ✅ 已实现 | — |
| 模拟只读仪表盘 | ✅ 已实现 | test_dashboard.py |
| GOS安装/回滚脚本 | ✅ 已实现 | — |
| 官方文档入库 | ✅ 19份 | docs/official/ |

### 未完成现场验证

- 真实 TCP 状态连接与解析（等待 GOS 证据）
- RTSP 拉流与 Web 视频展示（endpoint 未批准时保持 UNVERIFIED）
- Web 单点导航控制
- 多点巡逻状态机
- 审计日志
- 数尔安防云台/视频适配

真实状态只有同时满足以下条件才可判定为 `REAL`：

```text
TARGET_IDENTITY_CONFIRMED=PASS
MESSAGE_PARSED=PASS
TELEMETRY_FRESH=PASS
```

TCP 建连、收到字节、HTTP 200、进程运行和端口监听都不能替代上述条件。

## 安全边界

本项目涉及移动机器人。**未完成现场确认前，不得发送运动、导航、步态、速度、定位重置、心跳或其他控制报文。**

- 程序只部署在 GOS；不修改 AOS/NOS 原厂服务、路由或原始地图
- realtime Web 服务绑定 manifest 指定的 GOS 地址 `10.21.31.104:8080`，控制开关关闭
- 没有真实消息时必须显示 `NO_DATA`、`STALE` 或 `ERROR`，不得显示为 `REAL`
- 建图为 `BLOCKED`，导航和所有控制报文禁止
- 仓库不得提交密码、Token、私钥、现场真实地图、视频或未脱敏日志

## 快速验证

```bash
# 运行全部测试
PYTHONPATH=. uv run --with pytest pytest -q
# 当前测试结果以本轮执行报告为准

# 编译检查
python3 -m compileall -q backend

# Diff 检查
git diff --check
```

## GOS 部署

```bash
bash deploy/scripts/deploy-readonly.sh --one-shot
```

入口会自动检查 GOS 上的 Python 3.8.10、systemd、运行账户、安装目录、固定地址、端口冲突和只读安全开关。部署前可先执行：

```bash
bash deploy/scripts/deploy-readonly.sh --preflight
bash deploy/scripts/deploy-readonly.sh --dry-run
```

`--dry-run` 必须输出 `NO_FILES_WRITTEN=true`、`NO_SYSTEMD_CHANGE=true` 和 `NO_NETWORK_SIDE_EFFECT=true`。任一前置条件失败都必须安全阻断；当前未取得 GOS 现场证据前，最终状态只能是 `BLOCKED` 或 `HOST_EXECUTION_REQUIRED`。

健康接口：

```text
http://10.21.31.104:8080/api/v1/health
http://10.21.31.104:8080/api/v1/status/latest
```

视频：manifest 未配置 RTSP endpoint 时保持 `UNVERIFIED`，不得猜测 URL 或启动 FFmpeg。完整说明见 [docs/06-deployment.md](./docs/06-deployment.md)。

## 当前发布与分支状态

- 当前历史 feature 分支：`feat/m20-readonly-one-shot-20260808`。
- 该分支尚未迁移到规范命名；建议后续使用 `feature/readonly-realtime` 或 `fix/<scope>`，不删除或重写现有历史。
- 未取得 GOS Python 3.8.10 和真实遥测证据前，不创建正式 SemVer tag 或 production release。
- GitHub feature 分支同步不代表 GOS 部署完成。

## 文档导航

| 文档 | 用途 |
|---|---|
| [01-overview.md](./01-overview.md) | 项目目标、范围、当前阶段 |
| [02-architecture.md](./02-architecture.md) | 系统架构、当前/目标拓扑、数据边界 |
| [03-modules.md](./03-modules.md) | 代码模块说明 |
| [04-requirements.md](./04-requirements.md) | 需求清单、状态、验收条件 |
| [05-testing.md](./05-testing.md) | 测试流程与验证标准 |
| [06-deployment.md](./06-deployment.md) | GOS安装、验证、回滚 |
| [07-changes.md](./07-changes.md) | 变更记录 |
| [procedures/mapping-test.md](./procedures/mapping-test.md) | 建图与定位测试操作手册 |
| [procedures/office-acceptance.md](./procedures/office-acceptance.md) | [测试场地]验收测试 |
| [reviews/v121-alignment.md](./reviews/v121-alignment.md) | V1.2.1代码对齐审查 |
| [reviews/blockers-fixed.md](./reviews/blockers-fixed.md) | 阻塞项修复报告 |
| [official-docs-review.md](./official-docs-review.md) | 官方资料台账与差异记录 |
| [docs/README.md](./README.md) | 官方资料库详细索引 |
