# M20 Pro GOS 现场部署指南

## 1. 适用范围

本指南用于山猫 M20 Pro 在 GOS `10.21.31.104` 本机执行真实状态订阅。当前不执行建图、导航、巡逻、云台、拍照或任何控制报文。

## 2. 固定目标

所有地址和端口以 `deploy/readonly-manifest.json` 为唯一配置来源：

```text
GOS=10.21.31.104
AOS=10.21.31.103
NOS=10.21.31.106
AOS_TCP=30001
AOS_UDP=30000
RTSP=8554
WEB=8080
```

不得使用旧地址 `10.21.31.101`，不得扫描网段或切换候选地址。

## 3. 获取已验证版本

在 GOS 本机执行，只允许 fast-forward：

```bash
cd /opt/data/m20-patrol-robot
git fetch origin --prune
git pull --ff-only origin main
git status --short
```

工作区有未提交修改时停止，并报告 `DIRTY_WORKTREE_BLOCKED`。不得执行 `reset --hard` 或 `clean -fd`。

## 4. 主机预检

```bash
hostname
ip -brief address
python3 --version
python3.8 -c 'import sys; print(sys.executable); print(sys.version)'
python3.8 -c 'import backend; print("IMPORT_OK")'
systemctl --user is-system-running
ss -ltnup
```

必须确认：

- 主机地址包含 `10.21.31.104`；
- Python 为实际 3.8.x 运行时；
- user systemd 可用；
- AOS 固定目标路由可达；
- 不存在冲突服务 `m20-patrol-realtime.service` active 或 enabled。

## 5. 唯一部署命令

```bash
bash deploy/scripts/deploy-readonly.sh --preflight
bash deploy/scripts/deploy-readonly.sh --one-shot
```

`--one-shot` 会自动执行 manifest 校验、Python 版本检查、release/venv/unit/current 事务、服务启动和严格健康检查。

安全开关必须保持：

```text
M20_RUNTIME_MODE=realtime_readonly（保留，为系统配置键）
READ_ONLY_MODE=true
CONTROL_ENABLED=false
TELEMETRY_RX_ENABLED=true
TELEMETRY_TX_ENABLED=false
WEB_REALTIME_ENABLED=true
```

## 6. 严格验证

```bash
systemctl --user status m20-patrol-readonly.service --no-pager
curl --fail --silent --show-error http://10.21.31.104:8080/api/v1/health
curl --fail --silent --show-error http://10.21.31.104:8080/api/v1/status/latest
ss -ltnup
```

只有以下条件全部成立，才可报告真实状态新鲜可观测：

```text
healthy=true
source=REAL
connected=true
valid_frames>0
message_parsed=true
status_accepted=true
age_ms < stale_after_seconds*1000
```

HTTP 200、进程存在、端口监听和页面可打开均不能替代真实遥测证据。

## 7. 视频边界

RTSP endpoint 未由 manifest 或现场批准配置明确提供时，不启动 FFmpeg，视频标记为 `UNVERIFIED`。不得使用猜测地址。

## 8. 停止和回滚

```bash
systemctl --user stop m20-patrol-readonly.service
bash deploy/scripts/deploy-readonly.sh --rollback <INSTALLED_COMMIT_SHA>
```

回滚目标必须通过 manifest、固定地址、服务模板、入口文件和 Python 版本校验。不得停止、删除或修改未知用户服务。

## 9. 禁止操作

- 发送 Type=100/Command=100 心跳；
- 发送运动、导航、巡逻、云台、拍照或建图报文；
- 修改 AOS/NOS 配置、网络、路由、防火墙或系统级 systemd；
- 使用 `pkill -9 -f`、广泛 kill、`reset --hard`、`clean -fd`；
- 将模拟、缓存或旧日志写成真实状态。
