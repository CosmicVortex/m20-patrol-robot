# 山猫 M20 Pro 巡逻项目

山猫 M20 Pro 巡逻安防系统的二次开发代码库。部署在 M20 Pro 的 GOS（用户开发主机）上，通过 basic_server 协议与 AOS（运动主机）通信，实现状态监控、视频回传和受控导航。

## 项目身份

- **唯一型号**：山猫 M20 Pro（不使用 PRO/STD 等软件型号枚举）
- **演示阶段场地**：华翔智行办公室
- **目标部署场地**：东莞中升之星奔驰 4S 店
- **实施顺序**：办公室先完成建图、状态接入、视频切换、单点导航控制验收；全部通过后，门店重新建图并单独验收
- **部署主机**：GOS（10.21.31.104，候选值，须现场签认）
- **当前阶段**：离线基线完成，等待办公室实机准入

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

### 未实现（等待实机准入）

- 真实 TCP 状态连接与解析
- RTSP 拉流与 Web 视频展示
- Web 单点导航控制
- 多点巡逻状态机
- 审计日志
- 数尔安防云台/视频适配

## 安全边界

本项目涉及移动机器人。**未完成现场确认前，不得发送运动、导航、步态、速度、定位重置、心跳或其他控制报文。**

- 程序只部署在 GOS；不修改 AOS/NOS 原厂服务、路由或原始地图
- 当前服务只绑定 `127.0.0.1`，控制开关默认为关闭
- 模拟状态必须标注 `SIMULATED`，不得显示为真实设备状态
- 仓库不得提交密码、Token、私钥、现场真实地图、视频或未脱敏日志

## 快速验证

```bash
# 运行全部测试
PYTHONPATH=. uv run --with pytest pytest -q
# 76 passed

# 编译检查
python3 -m compileall -q backend

# Diff 检查
git diff --check
```

## GOS 部署

```bash
bash deploy/scripts/install-gos.sh --repo /path/to/m20-patrol-robot --ref <approved-commit>
```

安装前须确认：GOS 上的 Python、systemd、运行账户、安装目录和现场批准的提交。完整说明见 [docs/06-deployment.md](./06-deployment.md)。

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
| [procedures/office-acceptance.md](./procedures/office-acceptance.md) | 办公室验收测试 |
| [reviews/v121-alignment.md](./reviews/v121-alignment.md) | V1.2.1代码对齐审查 |
| [reviews/blockers-fixed.md](./reviews/blockers-fixed.md) | 阻塞项修复报告 |
| [official-docs-review.md](./official-docs-review.md) | 官方资料台账与差异记录 |
| [docs/README.md](./README.md) | 官方资料库详细索引 |
