# 06 — 部署流程

## 一键部署

```bash
cd /opt/data/m20-patrol-robot
bash deploy/scripts/deploy-readonly.sh --one-shot
```

执行位置：GOS 本机。

## 支持模式

```bash
bash deploy/scripts/deploy-readonly.sh --preflight   # 预检
bash deploy/scripts/deploy-readonly.sh --dry-run     # 试运行
bash deploy/scripts/deploy-readonly.sh --install     # 安装
bash deploy/scripts/deploy-readonly.sh --start       # 启动
bash deploy/scripts/deploy-readonly.sh --status      # 状态
bash deploy/scripts/deploy-readonly.sh --rollback <SHA>  # 回滚
```

参数来自 `deploy/readonly-manifest.json`。

## 环境变量

```
M20_RUNTIME_MODE=realtime_readonly（保留，为系统配置键）
M20_READ_ONLY_MODE=true
M20_CONTROL_ENABLED=false
M20_TELEMETRY_RX_ENABLED=true
M20_TELEMETRY_TX_ENABLED=false
M20_WEB_REALTIME_ENABLED=true
```

## 健康检查

```bash
curl http://10.21.31.104:8080/api/v1/health
curl http://10.21.31.104:8080/api/v1/status/latest
systemctl --user status m20-patrol-readonly.service
```

通过条件：
```
source=REAL, connected=true, valid_frames>0, age_ms < stale_after_seconds*1000
```

HTTP 200 不能替代真实遥测证据。

## 停止与回滚

```bash
systemctl --user stop m20-patrol-readonly.service
bash deploy/scripts/deploy-readonly.sh --rollback <SHA>
```
