# 巡检机器人

M20 Pro 巡逻机器狗的二次开发项目。当前版本提供只读状态监控功能：通过 basic_server 协议从 AOS 接收状态数据，不执行导航、巡逻、云台、拍照等控制操作。

## 硬件与部署

| 项目 | 值 |
|------|-----|
| 机器型号 | 山猫 M20 Pro |
| GOS 主机 | 10.21.31.104 |
| AOS 主机 | 10.21.31.103 |
| NOS 主机 | 13.21.31.106 |
| 当前阶段 | 云端代码完成，待 GOS 现场部署验证 |

## 端口配置

所有地址和端口配置在 `deploy/readonly-manifest.json` 中，不得手工修改。

| 服务 | 端口 | 用途 |
|------|------|------|
| basic_server TCP | 30001 | 状态订阅 |
| basic_server UDP | 30000 | 高频指令 |
| RTSP | 8554 | 视频流 |
| Web | 8080 | 仪表盘 |

## 安全配置

```
M20_RUNTIME_MODE=realtime_readonly
READ_ONLY_MODE=true
CONTROL_ENABLED=false
TELEMETRY_RX_ENABLED=true
TELEMETRY_TX_ENABLED=false
WEB_REALTIME_ENABLED=true
```

当前版本只接收状态数据，不发送任何控制命令。导航、巡逻、建图等功能尚未启用。

## 功能清单

### 已完成（离线测试）

| 功能 | 状态 | 测试文件 |
|------|------|----------|
| APDU 帧编解码 | ✅ | test_frame.py |
| 状态消息解析 | ✅ | test_status.py |
| TCP 客户端 + 门禁 | ✅ | test_basic_client.py |
| 导航报文构造 | ✅ | test_navigation_v010.py |
| 视频流管理器 | ✅ | — |
| 模拟仪表盘 | ✅ | test_dashboard.py |
| 部署脚本 | ✅ | — |
| 官方文档入库 | ✅ | 19份 |

### 待现场验证

- 真实 TCP 状态连接
- RTSP 视频接入
- Web 单点导航控制
- 多点巡逻功能
- 云台适配

## 验证命令

```bash
# 运行测试
PYTHONPATH=. uv run --with pytest pytest -q

# 编译检查
python3 -m compileall -q backend

# 部署
bash deploy/scripts/deploy-readonly.sh --one-shot
```

## 健康检查

```bash
curl http://10.21.31.104:8080/api/v1/health
curl http://10.21.31.104:8080/api/v1/status/latest
```

真实数据需满足：`source=REAL`、`message_parsed=true`、`telemetry_fresh=true`。

## 分支策略

- `main`：唯一稳定分支
- `v0.1.0-draft`：当前云端基线版本

## 文档

```
docs/
├── index.md              # 导航
├── 01-overview.md        # 项目概览
├── 02-architecture.md    # 系统架构
├── 03-modules.md         # 模块说明
├── 04-requirements.md    # 需求清单
├── 05-testing.md         # 测试流程
├── 06-deployment.md      # 部署流程
├── 07-changes.md         # 变更记录
├── 08-branch-policy.md   # 分支策略
├── 09-official-docs.md   # 官方文档索引
├── procedures/           # 操作手册
├── reviews/              # 审查记录
└── official/             # 官方文档（只读）
```

## 注意事项

- 仓库不得包含密码、Token、私钥
- 地图资产需记录 SHA-256 哈希
- [测试场地]地图不得直接用于[客户场地]
