#!/bin/bash
# M20 Patrol Robot - 快速启动脚本
# 适配 GOS Python 3.8.10 环境

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
D="${SCRIPT_DIR}"

echo "=== M20 巡逻机器人启动脚本 ==="
echo "脚本目录：${SCRIPT_DIR}"
echo ""

# Python 3.8 兼容性检查
echo "[1/4] 检查 Python 环境..."
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "    Python 版本：${PYTHON_VERSION}"

# 验证编译
echo "[2/4] 验证代码编译..."
if python3 -m compileall -q "${D}/backend/" 2>/dev/null; then
    echo "    ✓ 编译通过"
else
    echo "    ✗ 编译失败"
    exit 1
fi

# 停止旧进程
echo "[3/4] 停止旧服务..."
pkill -9 -f "python3.*dashboard" 2>/dev/null || true
sleep 1

# 启动服务
echo "[4/4] 启动服务..."
cd "$D"

# 检查依赖
if python3 -c "import fastapi" 2>/dev/null; then
    echo "    检测到 fastapi，尝试启动完整版..."
    nohup python3 -c "
import sys
sys.path.insert(0, '.')
from backend.app.dashboard_realtime import serve_dashboard
serve_dashboard(host='127.0.0.1', port=8080, aos_host='10.21.31.103')
" > /tmp/dashboard_realtime.log 2>&1 &
else
    echo "    启动简化版（无外部依赖）..."
    nohup python3 backend/app/dashboard_simple.py > /tmp/dashboard_simple.log 2>&1 &
fi

DASHBOARD_PID=$!
echo "    服务 PID: $DASHBOARD_PID"

# 等待服务启动
echo "    等待服务启动..."
for i in $(seq 1 10); do
    if curl -s http://127.0.0.1:8080/api/v1/health > /dev/null 2>&1; then
        echo "    ✓ 服务启动成功"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "    ✗ 服务启动超时"
        echo "    查看日志：cat /tmp/dashboard_simple.log"
        exit 1
    fi
    sleep 1
done

echo ""
echo "=========================================="
echo "访问地址：http://127.0.0.1:8080/"
echo ""
echo "从笔记本访问请执行："
echo "  ssh -L 8080:127.0.0.1:8080 user@10.21.31.104"
echo ""
echo "停止服务："
echo "  pkill -f dashboard"
echo "=========================================="
