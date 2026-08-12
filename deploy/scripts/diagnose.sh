#!/usr/bin/env bash
# 诊断脚本：检查M20服务状态和端口占用
# 在GOS上运行: bash diagnose.sh

set -euo pipefail

echo "=== GOS环境诊断 ==="
echo ""

# 1. 检查Python进程
echo "[1] 检查Python进程..."
ps aux | grep 'm20-patrol\|backend.app.server' | grep -v grep || echo "  无相关进程"
echo ""

# 2. 检查端口占用
echo "[2] 检查端口8080占用..."
if netstat -tlnp 2>/dev/null | grep -q ':8080'; then
    echo "  端口8080被占用:"
    netstat -tlnp 2>/dev/null | grep ':8080'
else
    echo "  端口8080空闲"
fi
echo ""

# 3. 检查服务状态
echo "[3] 检查systemd服务状态..."
systemctl --user status m20-patrol-readonly.service --no-pager -l 2>/dev/null || echo "  服务未运行"
echo ""

# 4. 检查最近的日志
echo "[4] 最近日志（最后30行）..."
journalctl --user -u m20-patrol-readonly.service --no-pager -n 30 2>/dev/null || echo "  无日志"
echo ""

# 5. 检查配置文件
echo "[5] 配置文件检查..."
if [ -f ~/m20-patrol-robot/deploy/readonly-manifest.json ]; then
    echo "  manifest存在"
    cat ~/m20-patrol-robot/deploy/readonly-manifest.json
else
    echo "  ERROR: manifest不存在"
fi
echo ""

# 6. 检查密码文件
echo "[6] 密码文件..."
if [ -f ~/.config/m20-patrol/passwords.env ]; then
    echo "  密码文件存在"
    ls -la ~/.config/m20-patrol/passwords.env
else
    echo "  WARNING: 密码文件不存在"
fi
echo ""

# 7. 检查静态资源
echo "[7] 静态资源检查..."
for f in \
    ~/m20-patrol-robot/docs/website/index.html \
    ~/m20-patrol-robot/docs/website/js/app.js \
    ~/m20-patrol-robot/docs/website/js/views/dashboard.js \
    ~/m20-patrol-robot/docs/website/robot-dog.png \
    ~/m20-patrol-robot/docs/website/robot-dog.jpg; do
    if [ -f "$f" ]; then
        echo "  ✓ $f ($(wc -c < "$f") bytes)"
    else
        echo "  ✗ MISSING: $f"
    fi
done
echo ""

# 8. 尝试重启服务
echo "[8] 建议操作:"
echo "  如果服务未运行或端口冲突，请执行:"
echo "  systemctl --user restart m20-patrol-readonly.service"
echo "  bash deploy/scripts/deploy-readonly.sh --restart"
