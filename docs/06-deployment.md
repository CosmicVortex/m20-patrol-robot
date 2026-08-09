# 06 — 部署流程

## 一键部署

```bash
cd /opt/data/m20-patrol-robot
bash deploy/scripts/deploy-readonly.sh --one-shot
```

执行位置必须是 GOS 本机。

## 支持的模式

```bash
bash deploy/scripts/deploy-readonly.sh --preflight    # 预检
bash deploy/scripts/deploy-readonly.sh --dry-run      # 试运行
bash deploy/scripts/deploy-readonly.sh --install      # 安装
bash deploy/scripts/deploy-readonly.sh --start        # 启动
bash deploy/scripts/deploy-readonly.sh --status       # 状态
bash deploy/scripts/deploy-readonly.sh --rollback <SHA> # 回滚
```

## 固定目标

参数来自 `deploy/readonly-manifest.json`。

| 变量 | 值 |
|------|-----|
| GOS_HOST | 10.21.31.104 |
| AOS_HOST | 10.21.31.103 |
| NOS_HOST | 10.21.31.106 |
| AOS_TCP_PORT | 30001 |
| AOS_UDP_PORT | 30000 |
| RTSP_PORT | 8554 |
| WEB_PORT | 8080 |

## 安全边界

```
M20_RUNTIME_MODE=realtime_readonly
READ_ONLY_MODE=true
CONTROL_ENABLED=false
TELEMETRY_RX_ENABLED=true
TELEMETRY_TX_ENABLED=false
WEB_REALTIME_ENABLED=true
```

本周期接收非控制类实时状态数据。不发送心跳、运动、导航、巡逻、云台、拍照或建图报文。

## Preflight 检查

`--preflight` 检查项：

- 主机身份包含 `10.21.31.104`
- Python 为实际 3.8.x 运行时
- user systemd 可用
- RX/TX、控制开关一致
- Web 绑定正确地址和 `8080` 端口
- 无旧地址或未解决凭据

## 健康判定

健康 API：
```
http://10.21.31.104:8080/api/v1/health
http://10.21.31.104:8080/api/v1/status/latest
```

必须同时满足：
```
healthy=true
source=REAL
connected=true
message_parsed=true
status_accepted=true
age_ms < stale_after_seconds * 1000
```

## 回滚

```bash
bash deploy/scripts/deploy-readonly.sh --rollback <COMMIT_SHA>
```

回滚前记录当前 `current`、unit 和 active/enabled 状态。
