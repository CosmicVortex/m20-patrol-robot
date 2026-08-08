# 06 — 只读一键部署

## 1. 唯一推荐入口

本项目当前只读实时部署的唯一推荐入口是：

```bash
cd /opt/data/m20-patrol-robot
bash deploy/scripts/deploy-readonly.sh --one-shot
```

执行位置必须是 GOS `10.21.31.104` 本机。云端测试、模拟服务和端口监听不能替代 GOS 现场证据。

支持的模式：

```bash
bash deploy/scripts/deploy-readonly.sh --preflight
bash deploy/scripts/deploy-readonly.sh --dry-run
bash deploy/scripts/deploy-readonly.sh --install
bash deploy/scripts/deploy-readonly.sh --start
bash deploy/scripts/deploy-readonly.sh --status
bash deploy/scripts/deploy-readonly.sh --rollback <COMMIT_SHA>
bash deploy/scripts/deploy-readonly.sh --one-shot
```

## 2. 固定目标和端口

参数来自版本化 `deploy/readonly-manifest.json`。不得手工修改源代码，不得扫描地址或切换候选地址。

```text
GOS_HOST=10.21.31.104
AOS_HOST=10.21.31.103
NOS_HOST=13.21.31.106
AOS_TCP_PORT=30001
AOS_UDP_PORT=30000
RTSP_PORT=8554
WEB_PORT=8080
```

已废弃地址 `10.21.31.101` 不得使用。

## 3. 运行安全边界

```text
M20_RUNTIME_MODE=realtime_readonly
READ_ONLY_MODE=true
CONTROL_ENABLED=false
TELEMETRY_RX_ENABLED=true
TELEMETRY_TX_ENABLED=false
WEB_REALTIME_ENABLED=true
```

本周期只接收非控制类实时数据。不会自动发送 Type=100/Command=100 心跳，也不会发送运动、导航、巡逻、云台、拍照或建图报文。

RTSP endpoint 未由 manifest 或现场批准配置明确提供时，视频保持 `UNVERIFIED`，不启动 FFmpeg。

## 4. Preflight 检查

`--preflight` 必须在 GOS 本机执行，并检查：

- 主机身份必须包含 `10.21.31.104`；
- Python 必须是实际 Python 3.8.x 运行时；
- realtime dashboard、manifest 和 user systemd 可用；
- 只读、RX/TX、控制开关一致；
- 冲突 realtime service 不得 active 或 enabled；
- Web 绑定为 manifest 指定的 GOS 地址和 `8080`；
- AOS 固定地址和 `30001` 已加载；
- 不存在旧地址、未解决模板或凭据。

没有真实 Python 3.8.x、systemd、正确主机身份或固定目标路由时，必须安全失败。

## 5. 一键执行顺序

```text
读取 manifest
→ 检查 GOS 身份和 Python 3.8.x
→ 检查 user systemd、磁盘和冲突服务
→ 创建固定 commit release
→ 创建并验证 Python 3.8.x venv
→ 执行离线测试和 compileall
→ 写入用户 unit
→ 切换 current
→ 启动 realtime_readonly
→ 访问严格 health/status API
→ 解析真实遥测证据
```

失败时恢复原 `current`、unit 和服务状态，不删除未知目录或用户文件。

## 6. 严格健康判定

健康 API：

```text
http://10.21.31.104:8080/api/v1/health
```

状态 API：

```text
http://10.21.31.104:8080/api/v1/status/latest
```

HTTP 200 或端口监听不代表真实通信成功。必须同时满足：

```text
healthy=true
runtime_mode=realtime_readonly
read_only_mode=true
control_enabled=false
telemetry_tx_enabled=false
source=REAL
connected=true
valid_frames>0
message_parsed=true
status_accepted=true
0 <= age_ms < stale_after_seconds * 1000
```

证据分层如下：

```text
NETWORK_READY
→ TCP_CONNECTED
→ BYTES_RECEIVED
→ FRAME_VALID
→ MESSAGE_PARSED
→ STATUS_ACCEPTED
→ TELEMETRY_FRESH
```

只有最后一项通过，才可报告真实遥测新鲜可观测。

## 7. 现场取证命令

在 GOS 本机保存输出和退出码：

```bash
hostname
ip -brief address
python3 --version
command -v python3.8 || true
python3.8 -c 'import sys; print(sys.executable); print(sys.version)'
python3.8 -c 'import backend; print("IMPORT_OK")'
systemctl --user is-system-running
systemctl --user status m20-patrol-readonly.service --no-pager
ss -ltnup
curl --fail --silent --show-error http://10.21.31.104:8080/api/v1/health
curl --fail --silent --show-error http://10.21.31.104:8080/api/v1/status/latest
```

## 8. 回滚

回滚目标必须是已安装且通过只读 manifest 校验的完整 commit release。不得回滚到仅有旧 dashboard、旧地址或非只读配置的目录。

```bash
bash deploy/scripts/deploy-readonly.sh --rollback <COMMIT_SHA>
```

回滚前应记录：

- 当前 `current`；
- 当前 unit；
- active/enabled 状态；
- 目标 release SHA256。

## 9. 现场结论

允许的最终结论只有：

```text
READY_FOR_HOST_ONE_SHOT_REALTIME_READONLY
DEPLOYED_BUT_REAL_DATA_BLOCKED
BLOCKED
HOST_EXECUTION_REQUIRED
DIRTY_WORKTREE_BLOCKED
```

云端只能报告：

```text
CLOUD_ENV_READY_GOS_EXECUTION_REQUIRED
```

建图保持 `BLOCKED`，导航保持禁止。
