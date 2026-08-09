# M20 Pro 只读实时观测系统

M20 Pro 巡逻安防系统的二次开发代码库。当前 release 仅提供 GOS 上的非控制实时状态观测：通过 basic_server 协议从 AOS 接收状态数据，不启动导航、巡逻、云台、拍照或其他控制路径。

## 项目标识

| 字段 | 值 |
|------|------|
| 机器型号 | 山猫 M20 Pro（单一型号，无 PRO/STD 区分） |
| 演示场地 | [内部测试场地] |
| 目标场地 | [客户场地] |
| 部署顺序 | [测试场地] 验收通过后，[客户场地] 重新建图并单独验收 |
| GOS 主机 | 10.21.31.104（项目负责人确认固定地址） |
| 当前状态 | `CLOUD_ENV_READY_GOS_EXECUTION_REQUIRED` |

## 固定目标与端口

配置唯一来源：`deploy/readonly-manifest.json`。不得手工修改源代码或切换地址。

| 主机 | IP | 用途 |
|------|-----|------|
| GOS | 10.21.31.104 | 用户开发主机、Web 服务 |
| AOS | 10.21.31.103 | 运动控制、basic_server TCP/UDP |
| NOS | 13.21.31.106 | 建图、定位、导航 |

| 服务 | 协议 | 端口 |
|------|------|------|
| basic_server TCP | APDU/ASDU JSON | 30001 |
| basic_server UDP | APDU/ASDU JSON | 30000 |
| RTSP | H.264/H.265 | 8554 |
| Web HTTP | JSON | 8080 |
| Web WebSocket | — | 8080 |

已废弃地址 `10.21.31.101` 禁止使用。

## 安全边界

当前 release 运行模式：

```
M20_RUNTIME_MODE=realtime_readonly
READ_ONLY_MODE=true
CONTROL_ENABLED=false
TELEMETRY_RX_ENABLED=true
TELEMETRY_TX_ENABLED=false
WEB_REALTIME_ENABLED=true
```

**禁止操作**：建图、导航、巡逻、运动、云台、拍照和控制报文均不属于本 release 范围。

未获得 GOS 现场证据前，不得发送运动、导航、步态、速度、定位重置、心跳或其他控制报文。

## 当前交付物

### 离线验证完成

| 能力 | 状态 | 测试文件 |
|------|------|----------|
| APDU 16字节帧编解码 | ✅ | `protocol/test_frame.py` |
| JSON/XML PatrolDevice 信封 | ✅ | `protocol/test_messages.py` |
| 状态消息解析（1002/3,4,5,6; 1007/1,2,3; 2002/1） | ✅ | `test_status.py` |
| TCP 客户端 + 门禁 + message_id 关联 | ✅ | `test_basic_client.py` |
| 导航报文构造 + 安全门控 | ✅ | `test_navigation_v010.py` |
| 视频流管理器（RTSP 地址模型） | ✅ | — |
| 模拟只读仪表盘 | ✅ | `test_dashboard.py` |
| GOS 安装/回滚脚本 | ✅ | — |
| 官方文档入库 | ✅ | 19份 `docs/official/` |

### 待 GOS 现场验证

- 真实 TCP 状态连接与解析（等待 GOS 证据）
- RTSP 拉流与 Web 视频展示（endpoint 未批准时保持 `UNVERIFIED`）
- Web 单点导航控制
- 多点巡逻状态机
- 审计日志
- 云台/视频适配

## 真实状态判定标准

```text
TARGET_IDENTITY_CONFIRMED=PASS
MESSAGE_PARSED=PASS
TELEMETRY_FRESH=PASS
```

TCP 建连、收到字节、HTTP 200、进程运行和端口监听均不能替代上述条件。

## 快速验证

```bash
# 运行全部测试
PYTHONPATH=. uv run --with pytest pytest -q

# 编译检查
python3 -m compileall -q backend

# Diff 检查
git diff --check
```

## GOS 部署

```bash
# 预检
bash deploy/scripts/deploy-readonly.sh --preflight

# Dry-run（必须输出 NO_FILES_WRITTEN=true）
bash deploy/scripts/deploy-readonly.sh --dry-run

# 一键部署（必须在 GOS 本机执行）
bash deploy/scripts/deploy-readonly.sh --one-shot
```

健康检查：

```
http://10.21.31.104:8080/api/v1/health
http://10.21.31.104:8080/api/v1/status/latest
```

`--dry-run` 必须输出 `NO_FILES_WRITTEN=true`、`NO_SYSTEMD_CHANGE=true` 和 `NO_NETWORK_SIDE_EFFECT=true`。未取得 GOS 现场证据前，最终状态为 `CLOUD_ENV_READY_GOS_EXECUTION_REQUIRED`。

## 分支与版本

- 当前 feature 分支：`feat/m20-readonly-one-shot-20260808`
- 未取得 GOS Python 3.8.10 和真实遥测证据前，不创建 SemVer tag 或 production release
- GitHub feature 分支同步不代表 GOS 部署完成

## 文档结构

```
docs/
├── 00-index.md              # 导航入口
├── 01-overview.md           # 项目概览
├── 02-architecture.md       # 系统架构
├── 03-modules.md            # 模块说明
├── 04-requirements.md       # 需求清单
├── 05-testing.md            # 测试流程
├── 06-deployment.md         # 部署流程
├── 07-changes.md            # 变更记录
├── procedures/              # 现场操作手册
│   ├── deployment-guide.md
│   ├── mapping-test.md
│   └── office-acceptance.md
├── reviews/                 # 审查记录
│   ├── v121-alignment.md
│   ├── blockers-fixed.md
│   └── comprehensive-audit-20260809.md
├── official-docs-review.md  # 官方资料台账
└── official/                # 官方文档（只读，19份）
```

## 安全须知

- 仓库不得提交密码、Token、私钥、现场真实地图、视频或未脱敏日志
- 地图资产必须以现场核验的地图身份、生成时间、场地和整包 SHA-256 联合记录
- [测试场地] 地图不得直接带入 [客户场地]
