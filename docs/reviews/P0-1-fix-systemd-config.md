# P0-1: 修正systemd服务配置

**问题**: systemd服务中端口和超时配置错误

**文件**: `deploy/systemd/m20-patrol-readonly.service`

**修改前**:
```ini
Environment=M20_TARGET_HOST=10.21.31.103
Environment=M20_TARGET_PORT=8888
Environment=M20_STALE_AFTER_SECONDS=300
```

**修改后**:
```ini
Environment=M20_STALE_AFTER_SECONDS=3
```

**验证**:
```bash
grep M20_STALE deploy/systemd/m20-patrol-readonly.service
# 应输出: Environment=M20_STALE_AFTER_SECONDS=3
```
