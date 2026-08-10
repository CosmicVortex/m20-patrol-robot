#!/usr/bin/env bash
# M20 Patrol Robot - 诊断脚本
set -euo pipefail

TARGET_ROOT="$HOME/m20-patrol-robot"

echo "=== M20 Patrol Robot 诊断 ==="
echo ""

echo "1. 检查Python版本"
python3 --version
echo ""

echo "2. 检查端口占用"
echo "   8080端口:"
netstat -tlnp 2>/dev/null | grep :8080 || echo "   未被占用"
echo ""

echo "3. 检查AOS连接"
echo "   测试连接10.21.31.103:30001..."
timeout 3 bash -c 'echo > /dev/tcp/10.21.31.103/30001' 2>/dev/null && echo "   ✓ 连接成功" || echo "   ✗ 连接失败"
echo ""

echo "4. 检查服务状态"
systemctl --user status m20-patrol-readonly --no-pager || echo "   服务未运行"
echo ""

echo "5. 检查日志"
journalctl --user -u m20-patrol-readonly -n 20 --no-pager 2>/dev/null || echo "   无日志"
echo ""

echo "6. 手动测试服务"
echo "   启动服务(5秒后自动停止)..."
cd "$TARGET_ROOT"
timeout 5 PYTHONPATH=. python3 -m backend.app.server --manifest deploy/readonly-manifest.json --verbose 2>&1 | head -30 || echo "   服务已停止"
echo ""

echo "7. 检查健康API"
curl -s http://127.0.0.1:8080/api/v1/health 2>/dev/null || echo "   API不可用"
echo ""

echo "=== 诊断完成 ==="
