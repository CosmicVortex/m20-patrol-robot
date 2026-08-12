#!/usr/bin/env bash
# M20 服务深度诊断脚本 - 针对GOS环境
# 在GOS上运行: bash diagnose-gos.sh

set -euo pipefail

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║        M20 服务深度诊断 - GOS环境                         ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查项计数
CHECKS_PASSED=0
CHECKS_FAILED=0

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((CHECKS_PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((CHECKS_FAILED++))
}

check_warn() {
    echo -e "${YELLOW}!${NC} $1"
}

echo "【系统信息】"
echo "  主机名: $(hostname)"
echo "  架构: $(uname -m)"
echo "  OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"')"
echo "  Python: $(python3 --version 2>&1)"
echo ""

echo "【1. 端口监听状态】"
echo "  检查 8080-8090 端口..."
PORT_LISTEN=$(netstat -tlnp 2>/dev/null | grep -E ':808[0-9] ' || true)
if [ -n "$PORT_LISTEN" ]; then
    echo -e "  ${GREEN}发现监听:${NC}"
    echo "$PORT_LISTEN" | sed 's/^/    /'
    
    # 提取PID
    PID=$(echo "$PORT_LISTEN" | awk '{print $NF}' | cut -d/ -f2)
    if [ -n "$PID" ] && [ "$PID" != "-" ]; then
        echo "  占用进程 PID: $PID"
        ps -p "$PID" -o pid,cmd 2>/dev/null | head -5
    fi
else
    echo -e "  ${RED}无端口监听（服务未启动或绑定失败）${NC}"
fi
echo ""

echo "【2. Python进程状态】"
PS_OUTPUT=$(ps aux 2>/dev/null | grep -E 'backend.app.server|m20-patrol' | grep -v grep || true)
if [ -n "$PS_OUTPUT" ]; then
    echo "  发现相关进程:"
    echo "$PS_OUTPUT" | sed 's/^/    /'
    
    # 检查进程数
    PROC_COUNT=$(echo "$PS_OUTPUT" | wc -l)
    echo "  进程数量: $PROC_COUNT"
    
    if [ "$PROC_COUNT" -gt 2 ]; then
        check_warn "进程数量异常（正常应为1-2个）"
    fi
else
    check_fail "未发现M20相关进程"
fi
echo ""

echo "【3. systemd服务状态】"
SERVICE_STATUS=$(systemctl --user status m20-patrol-readonly.service --no-pager 2>&1 || true)
if echo "$SERVICE_STATUS" | grep -q "active (running)"; then
    check_pass "服务状态: active (running)"
elif echo "$SERVICE_STATUS" | grep -q "failed"; then
    check_fail "服务状态: failed"
elif echo "$SERVICE_STATUS" | grep -q "inactive"; then
    check_warn "服务状态: inactive (dead)"
else
    check_warn "无法确定服务状态"
fi

# 提取关键信息
echo "  启动时间: $(echo "$SERVICE_STATUS" | grep "Active:" | head -1)"
echo "  PID: $(echo "$SERVICE_STATUS" | grep "Main PID:" | awk '{print $3}')"
echo ""

echo "【4. 完整日志分析】"
echo "  最后30行日志:"
journalctl --user -u m20-patrol-readonly.service --no-pager -n 30 -l 2>/dev/null | tail -30 | sed 's/^/    /'
echo ""

# 检查关键日志
echo "  关键日志检查:"
LOG_OUTPUT=$(journalctl --user -u m20-patrol-readonly.service --no-pager -n 100 -l 2>/dev/null || true)

if echo "$LOG_OUTPUT" | grep -q "Web服务已启动\|M20 Web Service 已启动"; then
    check_pass "找到服务启动成功日志"
else
    check_fail "未找到服务启动成功日志"
fi

if echo "$LOG_OUTPUT" | grep -q "端口绑定成功"; then
    PORT_LINE=$(echo "$LOG_OUTPUT" | grep "端口绑定成功")
    echo "    $PORT_LINE"
    check_pass "端口绑定成功"
elif echo "$LOG_OUTPUT" | grep -q "无法绑定"; then
    PORT_LINE=$(echo "$LOG_OUTPUT" | grep "无法绑定")
    echo "    $PORT_LINE"
    check_fail "端口绑定失败"
elif echo "$LOG_OUTPUT" | grep -q "使用备用端口"; then
    PORT_LINE=$(echo "$LOG_OUTPUT" | grep "使用备用端口")
    echo "    $PORT_LINE"
    check_warn "服务运行在备用端口"
else
    check_warn "日志中没有端口绑定相关信息（可能被截断）"
fi
echo ""

echo "【5. 配置文件检查】"
MANIFEST="$HOME/m20-patrol-robot/deploy/readonly-manifest.json"
if [ -f "$MANIFEST" ]; then
    check_pass "manifest文件存在"
    echo "  内容:"
    cat "$MANIFEST" | sed 's/^/    /'
else
    check_fail "manifest文件不存在: $MANIFEST"
fi
echo ""

echo "【6. 静态资源检查】"
RESOURCES=(
    "$HOME/m20-patrol-robot/docs/website/index.html"
    "$HOME/m20-patrol-robot/docs/website/js/app.js"
    "$HOME/m20-patrol-robot/docs/website/js/views/dashboard.js"
    "$HOME/m20-patrol-robot/docs/website/robot-dog.png"
    "$HOME/m20-patrol-robot/docs/website/robot-dog.jpg"
)

for res in "${RESOURCES[@]}"; do
    if [ -f "$res" ]; then
        SIZE=$(wc -c < "$res")
        check_pass "$(basename "$res") ($SIZE bytes)"
    else
        check_fail "$(basename "$res") 缺失"
    fi
done
echo ""

echo "【7. 端口连通性测试】"
for PORT in 8080 8081 8082 8083 8084 8085; do
    TIMEOUT=$(timeout 2 bash -c "echo >/dev/tcp/127.0.0.1/$PORT" 2>/dev/null && echo "可连接" || echo "不可连接")
    if [ "$TIMEOUT" = "可连接" ]; then
        echo -e "  端口 $PORT: ${GREEN}可连接${NC}"
        # 尝试获取响应
        RESPONSE=$(curl -s -m 2 http://127.0.0.1:$PORT/api/v1/health 2>/dev/null || echo "无响应")
        if [ -n "$RESPONSE" ]; then
            echo -e "    响应: ${GREEN}$RESPONSE${NC}"
        fi
    else
        echo "  端口 $PORT: 不可连接"
    fi
done
echo ""

echo "【8. 网络配置】"
echo "  IP地址:"
ip addr show 2>/dev/null | grep -E 'inet ' | grep -v '127.0.0.1' | sed 's/^/    /' || echo "    无法获取"
echo ""

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                         诊断结果                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
echo "  通过: $CHECKS_PASSED | 失败: $CHECKS_FAILED"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}所有检查通过！${NC}"
    echo ""
    echo "如果网站仍无法访问，请检查："
    echo "  1. 浏览器地址是否正确: http://10.21.31.104:8080/"
    echo "  2. 防火墙设置"
    echo "  3. 网络连接状态"
elif [ $CHECKS_FAILED -eq 1 ] && echo "$CHECKS_FAILED" | grep -q "1"; then
    echo -e "${YELLOW}发现1个问题，建议按以下步骤修复:${NC}"
    echo ""
    echo "  方案1: 重启服务"
    echo "    systemctl --user restart m20-patrol-readonly.service"
    echo ""
    echo "  方案2: 完全重置"
    echo "    systemctl --user stop m20-patrol-readonly.service"
    echo "    pkill -f 'backend.app.server' || true"
    echo "    sleep 2"
    echo "    bash deploy/scripts/deploy-readonly.sh --one-shot"
else
    echo -e "${RED}发现多个问题，建议完全重置部署:${NC}"
    echo ""
    echo "  执行以下命令:"
    echo "    cd ~/m20-patrol-robot"
    echo "    bash deploy/scripts/deploy-readonly.sh --one-shot"
fi
echo ""
