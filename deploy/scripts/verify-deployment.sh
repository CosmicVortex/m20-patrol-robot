#!/bin/bash
# M20 Pro 一键验证脚本
# 用法: bash verify-deployment.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GOS_HOST="10.21.31.104"
WEB_PORT=8080

echo "========================================"
echo "  M20 Pro 部署验证"
echo "========================================"
echo ""

# 检查服务状态
echo "[1/4] 检查服务状态..."
if systemctl --user is-active m20-patrol-readonly.service &>/dev/null; then
    echo "  ✓ 服务运行中"
else
    echo "  ✗ 服务未运行"
    exit 1
fi

# 检查健康状态
echo ""
echo "[2/4] 检查健康状态..."
HEALTH=$(curl -s http://localhost:$WEB_PORT/api/v1/health 2>/dev/null || echo '{}')
if echo "$HEALTH" | grep -q '"healthy":true'; then
    echo "  ✓ 健康检查通过"
else
    echo "  ✗ 健康检查失败"
    echo "  响应: $HEALTH"
    exit 1
fi

# 检查API端点
echo ""
echo "[3/4] 检查API端点..."
ENDPOINTS=(
    "/api/v1/status/latest"
    "/api/v1/gimbal/state"
    "/api/v1/gimbal/scan"
    "/api/v1/video"
)

for endpoint in "${ENDPOINTS[@]}"; do
    if curl -sf "http://localhost:$WEB_PORT$endpoint" &>/dev/null; then
        echo "  ✓ $endpoint"
    else
        echo "  ⚠ $endpoint (可能未连接)"
    fi
done

# 检查系统信息
echo ""
echo "[4/4] 系统信息..."
echo "  GOS主机: $GOS_HOST"
echo "  访问地址: http://$GOS_HOST:$WEB_PORT/"
echo "  Python: $(python3 --version 2>&1)"
echo "  用户: $(whoami)"
echo ""

echo "========================================"
echo "  验证完成!"
echo "========================================"
echo ""
echo "访问Web界面:"
echo "  http://$GOS_HOST:$WEB_PORT/"
echo ""
