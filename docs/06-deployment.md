# 部署流程

> **重要**: 本文档区分两个环境：
> - **云端开发环境**: `/opt/data/m20-patrol-robot` (代码开发、测试)
> - **GOS运行环境**: `~/.local/share/m20-patrol-robot` (现场部署、运行)

## 环境路径对照

| 环境 | 路径 | 用途 |
|------|------|------|
| 云端开发 | `/opt/data/m20-patrol-robot` | 代码开发、测试、审查 |
| GOS运行 | `~/.local/share/m20-patrol-robot` | 现场部署、运行服务 |

## 部署前准备

### 1. 云端环境操作

```bash
# 在云端环境修改代码
cd /opt/data/m20-patrol-robot
# 修改代码、运行测试
PYTHONPATH=. uv run --with pytest pytest -q
# 提交推送
git add -A && git commit -m "fix: xxx" && git push
```

### 2. GOS环境部署

```bash
# SSH到GOS
ssh user@10.21.31.104

# 克隆代码（首次）
git clone <repo-url> ~/.local/share/m20-patrol-robot

# 进入项目目录
cd ~/.local/share/m20-patrol-robot

# 设置密码（首次）
mkdir -p ~/.config/m20-patrol
cat > ~/.config/m20-patrol/passwords.env <<EOF
export M20_GIMBAL_PASSWORD='your_password'
export M20_ADMIN_PASSWORD='your_password'
EOF
chmod 600 ~/.config/m20-patrol/passwords.env

# 执行部署
bash deploy/scripts/deploy-readonly.sh --one-shot
```

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
M20_GIMBAL_PASSWORD=（必填，云台密码）
M20_ADMIN_PASSWORD=（必填，Web服务密码）
```

## 健康检查

```bash
# 在GOS本机执行
curl http://127.0.0.1:8080/api/v1/health
curl http://127.0.0.1:8080/api/v1/status/latest
systemctl --user status m20-patrol-readonly.service
```

从笔记本访问：
```bash
ssh -L 8080:127.0.0.1:8080 user@10.21.31.104
curl http://127.0.0.1:8080/api/v1/health
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

## 密码管理

密码保存在 GOS 本机：`~/.config/m20-patrol/passwords.env`

```bash
# 查看已保存的密码（掩码）
bash deploy/scripts/deploy-readonly.sh --show-passwords
```

## 故障排查

### 服务未启动

```bash
# 查看服务状态
systemctl --user status m20-patrol-readonly.service

# 查看日志
journalctl --user -u m20-patrol-readonly.service -f
```

### 端口冲突

```bash
# 检查端口占用
netstat -tlnp | grep 8080

# 停止服务释放端口
systemctl --user stop m20-patrol-readonly.service
```

### 遥测无数据

```bash
# 检查AOS连接
curl http://127.0.0.1:8080/api/v1/status/latest

# 检查basic_server状态
curl http://10.21.31.103:8080/status
```
