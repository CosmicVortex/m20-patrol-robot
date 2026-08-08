# 05 — 测试与现场验证

## 1. 云端离线验证

当前 feature 分支在云端开发环境和隔离 Python 3.8.10 环境分别验证。

```bash
# Python 3.13 云端环境
uv run --with pytest python -m pytest -q

# Python 3.8.10 隔离环境
PYBIN=/opt/data/.runtime/m20-venv-py3810/bin/python
PYTHONPATH=. "$PYBIN" -m pip check
PYTHONPATH=. "$PYBIN" -m pytest -q

# 编译和差异
python3 -m compileall -q backend
PYTHONPATH=. "$PYBIN" -m compileall -q backend
git diff --check
```

当前已验证结果：

```text
Python 3.13：114 passed
Python 3.8.10：114 passed
pip check：通过
两版本 compileall：通过
```

这些是云端/隔离环境证据，不是 GOS 或真实 AOS 证据。

## 2. 部署入口检查

```bash
bash deploy/scripts/deploy-readonly.sh --dry-run
bash deploy/tests/test-install-gos-venv.sh
bash -n deploy/scripts/deploy-readonly.sh deploy/scripts/install-gos.sh deploy/scripts/rollback-gos.sh deploy/scripts/start.sh
```

`--dry-run` 必须输出：

```text
NO_FILES_WRITTEN=true
NO_SYSTEMD_CHANGE=true
NO_NETWORK_SIDE_EFFECT=true
```

## 3. 真实数据判定

GOS 本机必须逐层记录：

```text
NETWORK_READY
TCP_CONNECTED
BYTES_RECEIVED
FRAME_VALID
MESSAGE_PARSED
STATUS_ACCEPTED
TELEMETRY_FRESH
```

只有 `MESSAGE_PARSED` 和 `TELEMETRY_FRESH` 同时通过，才能报告 `REAL` 真实状态。端口监听、进程存在、HTTP 200、mock socket、缓存和模拟页面都不能替代真实数据。

## 4. GOS 现场证据命令

```bash
hostname
ip -brief address
python3 --version
python3.8 -c 'import sys; print(sys.executable); print(sys.version)'
python3.8 -c 'import backend; print("IMPORT_OK")'
systemctl --user is-system-running
systemctl --user status m20-patrol-readonly.service --no-pager
ss -ltnup
curl --fail --silent --show-error http://10.21.31.104:8080/api/v1/health
curl --fail --silent --show-error http://10.21.31.104:8080/api/v1/status/latest
```

## 5. 禁止项

测试阶段仍禁止：

- Type=100/Command=100 心跳；
- 运动、导航、巡逻、云台、拍照和建图报文；
- 修改 AOS/NOS 配置；
- 猜测 RTSP endpoint；
- 使用旧地址 `10.21.31.101`。

RTSP endpoint 未被 manifest 或现场批准配置明确提供时，视频状态为 `UNVERIFIED`。
