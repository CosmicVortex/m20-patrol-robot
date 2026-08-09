# M20 Pro 巡逻机器人二次开发

山猫 M20 Pro 机器狗巡逻安防系统二次开发项目。通过 `basic_server` 协议与 AOS 通信，提供状态监控、视频回传和受控导航能力。

## 硬件配置

| 组件 | IP 地址 | 职责 | 访问方式 |
|------|---------|------|----------|
| GOS | 10.21.31.104 | 用户开发机、Web 服务 | SSH/VNC 可访问 |
| AOS | 10.21.31.103 | 运动控制、basic_server、rl_deploy | ❌ 不可直接访问 |
| NOS | 10.21.31.106 | 建图、定位、导航、planner | SSH/VNC 可访问 |

## 端口配置

| 服务 | 协议 | 端口 | 用途 |
|------|------|------|------|
| basic_server TCP | APDU/ASDU JSON | 30001 | 状态订阅、任务下发 |
| basic_server UDP | APDU/ASDU JSON | 30000 | 高频速度指令（≥20Hz） |
| RTSP | H.265/H.264 | 8554 | 本体前后相机视频流 |
| Web HTTP | JSON | 8080 | 状态查询、控制请求 |
| Web WebSocket | — | 8080 | 状态推送、视频流 |

配置来源：`deploy/readonly-manifest.json`

## 安全配置

```
M20_RUNTIME_MODE=realtime_readonly
READ_ONLY_MODE=true
CONTROL_ENABLED=false
TELEMETRY_RX_ENABLED=true
TELEMETRY_TX_ENABLED=false
WEB_REALTIME_ENABLED=true
```

当前版本为只读模式，不发送控制命令。导航、运动、建图等功能需书面放行后启用。

## 功能状态

| 功能 | 状态 | 说明 |
|------|------|------|
| APDU/ASDU 帧编解码 | ✅ offline_verified | 16字节帧头，JSON/XML 信封 |
| 状态消息解析 | ✅ offline_verified | 1002/3,4,5,6 + 1007/1,2,3 + 2002/1 |
| TCP 客户端 + 门禁 | ✅ offline_verified | control_enabled 默认 False |
| 真实状态订阅 | ✅ offline_verified | TelemetryAdapter → AOS TCP 30001 |
| Web 服务入口 | ✅ offline_verified | systemd 部署模板 |
| 认证模块 | ✅ offline_verified | PBKDF2 + Session + Cookie |
| 导航报文构造 | ✅ offline_verified | 单点/取消/状态查询 |
| 视频管理器 | 🟡 framework | RTSP 地址已配置，拉流待实测 |
| 多点巡逻状态机 | 🔴 not_implemented | 待单点控制验收 |
| 云台适配 | 🔴 not_implemented | 待实物确认 |

## 验证命令

```bash
# 运行测试
PYTHONPATH=. uv run --with pytest pytest -q

# 编译检查
python3 -m compileall -q backend

# 部署（需在 GOS 本机执行）
bash deploy/scripts/deploy-readonly.sh --one-shot
```

## 健康检查

```bash
curl http://10.21.31.104:8080/api/v1/health
curl http://10.21.31.104:8080/api/v1/status/latest
```

真实数据判定条件：

```json
{
  "source": "REAL",
  "message_parsed": true,
  "telemetry_fresh": true
}
```

## 分支策略

- `main`：唯一稳定分支
- 版本标签：`v0.1.0-draft`（云端基线）、`v0.1.0`（首个可用版本）

## 文档结构

```
docs/
├── 01-overview.md       项目概览
├── 02-architecture.md   系统架构
├── 03-modules.md        模块说明
├── 04-requirements.md   需求清单
├── 05-testing.md        测试流程
├── 06-deployment.md     部署流程
├── 07-changes.md        变更记录
├── 08-branch-policy.md  分支策略
├── 09-official-docs.md  官方文档索引
├── 09-real-web-integration-contract.md  真实Web开发契约
├── 10-real-web-progress.md  集成进度
├── procedures/          操作手册
├── reviews/             审查记录
└── official/            官方文档（只读）
```

## 注意事项

- 仓库不得包含密码、Token、私钥
- 地图资产需记录 SHA-256 哈希
- 测试场地与正式场地地图不得混用
- 所有控制操作需书面放行
