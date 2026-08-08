#!/bin/bash
# M20 Patrol Robot - 快速启动脚本
# 适配 GOS Python 3.8.10 环境

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
MANIFEST="${ROOT}/deploy/readonly-manifest.json"
PYTHON_BIN="$(command -v python3.8 || true)"
[ -n "$PYTHON_BIN" ] || { echo "需要 python3.8" >&2; exit 1; }
"$PYTHON_BIN" -c 'import sys; assert sys.version_info[:3] == (3,8,10)' || { echo "需要 Python 3.8.10" >&2; exit 1; }
WEB_BIND_HOST="$($PYTHON_BIN - "$MANIFEST" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))["web_bind_host"])
PY
)"
WEB_PORT="$($PYTHON_BIN - "$MANIFEST" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))["ports"]["web"])
PY
)"
STALE_AFTER_MS="$($PYTHON_BIN - "$MANIFEST" <<'PY'
import json,sys
print(int(json.load(open(sys.argv[1]))["stale_after_seconds"] * 1000))
PY
)"

echo "=== M20 巡逻机器人启动脚本 ==="
echo "脚本目录：${SCRIPT_DIR}"
echo ""

# Python 3.8 兼容性检查
echo "[1/4] 检查 Python 环境..."
PYTHON_VERSION=$($PYTHON_BIN --version 2>&1 | cut -d' ' -f2)
echo "    Python 版本：${PYTHON_VERSION}"
case "${PYTHON_VERSION}" in
    3.8.10) ;;
    *) echo "    ✗ 需要真实 Python 3.8.10 运行时"; exit 1 ;;
esac

# 验证编译
echo "[2/4] 验证代码编译..."
if "$PYTHON_BIN" -m compileall -q "${ROOT}/backend/" 2>/dev/null; then
    echo "    ✓ 编译通过"
else
    echo "    ✗ 编译失败"
    exit 1
fi

# 只通过本项目的用户级 systemd 服务停止旧实例，避免误杀其他进程
echo "[3/4] 检查本项目服务..."
if command -v systemctl >/dev/null 2>&1 && systemctl --user is-active --quiet m20-patrol-realtime.service; then
    echo "    检测到冲突服务 m20-patrol-realtime.service 正在运行；拒绝启动"
    exit 1
fi
if command -v systemctl >/dev/null 2>&1 && systemctl --user is-enabled --quiet m20-patrol-realtime.service; then
    echo "    检测到冲突服务 m20-patrol-realtime.service 已启用；拒绝启动"
    exit 1
fi
if command -v systemctl >/dev/null 2>&1 && systemctl --user is-active --quiet m20-patrol-readonly.service; then
    echo "    本项目服务已运行；请使用 systemctl --user stop m20-patrol-readonly.service 管理它"
    exit 0
fi

echo "[4/4] 通过唯一部署入口启动 realtime_readonly..."
"${SCRIPT_DIR}/deploy-readonly.sh" --one-shot

# 等待服务启动
echo "    等待服务启动..."
for i in $(seq 1 10); do
    if curl -fsS "http://${WEB_BIND_HOST}:${WEB_PORT}/api/v1/health" | "$PYTHON_BIN" - "$STALE_AFTER_MS" -c 'import json,sys; d=json.load(sys.stdin); limit=int(sys.argv[1]); raise SystemExit(0 if d.get("healthy") is True and d.get("runtime_mode") == "realtime_readonly" and d.get("read_only_mode") is True and d.get("control_enabled") is False and d.get("telemetry_tx_enabled") is False and d.get("source") == "REAL" and d.get("connected") is True and d.get("valid_frames", 0) > 0 and isinstance(d.get("age_ms"), (int,float)) and 0 <= d.get("age_ms") < limit else 1)' >/dev/null 2>&1; then
        echo "    ✓ 服务启动成功"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "    ✗ 服务启动超时"
        echo "    查看日志：journalctl --user -u m20-patrol-readonly.service"
        exit 1
    fi
    sleep 1
done

echo ""
echo "=========================================="
echo "访问地址：http://${WEB_BIND_HOST}:${WEB_PORT}/"
echo ""
echo "从笔记本访问请执行："
echo "  ssh -L 8080:10.21.31.104:8080 user@10.21.31.104"
echo ""
echo "停止服务："
echo "  systemctl --user stop m20-patrol-readonly.service"
echo "=========================================="
