================================================================================
M20 Pro 真机一键部署执行报告
================================================================================

【执行环境】
EXECUTION_HOST=cloud-deployment-agent
EXECUTION_HOST_IDENTITY=CLOUD
PYTHON_CLOUD_VERSION=3.13.5
PYTHON_GOS_REQUIRED=3.8.10
PYTHON_GOS_RUNTIME=BLOCKED (需 GOS 本机)
ENVIRONMENT_ROLE=CLOUD_DEV
HOST_SYSTEMD_USER_AVAILABLE=FAIL

【最终结论】
FINAL_CONCLUSION=HOST_EXECUTION_REQUIRED

云端已完成代码修复、测试验证、版本固化和 GitHub 同步。
GOS 真机部署必须由 GOS 10.21.31.104 本机执行。

================================================================================
【仓库状态】
================================================================================

branch: feat/m20-readonly-one-shot-20260808
Local HEAD: dad47e3567f984da711de122dd6e7e4b43008807
Remote HEAD: dad47e3567f984da711de122dd6e7e4b43008807
GitHub 同步: PASS
工作区: CLEAN (0 files modified)
测试: 114 passed in 1.37s

================================================================================
【P0 修复项】
================================================================================

| P0 项 | 状态 |
|---|---|
| Python 3.8.10 强制阻断 | PASS |
| health/status 统一严格语义 | PASS |
| 安装事务闭环 | PASS |
| 单一配置来源 | PASS |
| 部署后真实证据 | BLOCKED (需 GOS) |
| Web 暴露边界 | PASS |
| 测试补齐 | PASS (114 tests) |

================================================================================
【安全开关验证】
================================================================================

M20_RUNTIME_MODE: realtime_readonly
READ_ONLY_MODE: true
CONTROL_ENABLED: false
TELEMETRY_TX_ENABLED: false
默认发送报文: 否

================================================================================
【固定地址与端口】
================================================================================

GOS_HOST=10.21.31.104
AOS_HOST=10.21.31.103
NOS_HOST=13.21.31.106
AOS_TCP_PORT=30001
AOS_UDP_PORT=30000
RTSP_PORT=8554 (UNVERIFIED - endpoint 未配置)
WEB_PORT=8080
WEB_BIND_HOST=10.21.31.104

已废弃地址 10.21.31.101: 代码中已清除，仅文档中有历史引用

================================================================================
【GOS 本机执行命令】
================================================================================

cd /opt/data/m20-patrol-robot
git fetch origin --prune
git checkout feat/m20-readonly-one-shot-20260808
git pull --ff-only origin feat/m20-readonly-one-shot-20260808
bash deploy/scripts/deploy-readonly.sh --preflight
bash deploy/scripts/deploy-readonly.sh --dry-run
bash deploy/scripts/deploy-readonly.sh --one-shot

================================================================================
【部署入口】
================================================================================

唯一推荐入口: bash deploy/scripts/deploy-readonly.sh --one-shot

支持模式:
  --preflight  只读检查，不写入文件
  --dry-run    展示将执行的本地变更，不写入文件
  --install    写入 GOS release、venv 和用户级 unit
  --start      启动 realtime_readonly 和 Web
  --status     严格健康检查
  --rollback   回滚到指定 commit
  --one-shot   preflight + install + start + health check

================================================================================
【代码变更摘要】
================================================================================

1. README.md: 完整重写，包含固定地址、安全边界、部署步骤
2. deploy/scripts/deploy-readonly.sh: 模板化地址，增强 health/status 校验
3. deploy/systemd/m20-patrol-readonly.service: 模板化地址和端口
4. deploy/scripts/install-gos.sh: 增强 release 验证、provenance 追踪
5. deploy/scripts/rollback-gos.sh: 增强版本校验、路径安全
6. deploy/scripts/start.sh: 更新健康检查、修复 ssh 语法
7. backend/app/robot/telemetry.py: 添加连接状态追踪字段
8. backend/app/dashboard_realtime.py: 添加 data_state 字段、严格校验
9. 执行总结报告: 完整版执行报告

================================================================================
【阻塞项】
================================================================================

BLOCKED (需 GOS 本机验证):
- PYTHON_3810_RUNTIME: 需 GOS 有 python3.8 解释器
- SYSTEMD_USER: 需 GOS 有 systemd user manager
- REAL_HOST_TELEMETRY: 需 GOS 能连接到 AOS 10.21.31.103:30001
- TELEMETRY_FRESH: 需 GOS 收到有效遥测数据

================================================================================
【下一步】
================================================================================

1. 在 GOS 10.21.31.104 上执行上述命令
2. 验证 Python 3.8.10 存在: python3.8 --version
3. 执行 preflight: bash deploy/scripts/deploy-readonly.sh --preflight
4. 执行 dry-run: bash deploy/scripts/deploy-readonly.sh --dry-run
5. 执行 one-shot: bash deploy/scripts/deploy-readonly.sh --one-shot
6. 验证真实遥测: curl http://10.21.31.104:8080/api/v1/health

================================================================================
报告时间: 2026-08-08
执行位置: 云端开发环境
状态: HOST_EXECUTION_REQUIRED
================================================================================
