#!/bin/bash
# M20 Pro 深度网络诊断脚本
# 在 GOS 主机上运行此脚本来诊断TCP连接问题

set -euo pipefail

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           M20 Pro 网络连通性深度诊断                       ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

AOS_HOST="10.21.31.103"
AOS_TCP_PORT=30001
AOS_UDP_PORT=30000
GOS_IP=$(hostname -I | awk '{print $1}')

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}!${NC} $1"
}

echo "【1. 本地网络配置】"
echo "  GOS IP: $GOS_IP"
ip addr show 2>/dev/null | grep -E "inet " | grep -v "127.0.0.1" | while read line; do
    echo "  $line"
done
echo ""

echo "【2. 目标可达性测试】"
echo "  测试 ping $AOS_HOST ..."
if ping -c 3 -W 2 "$AOS_HOST" >/dev/null 2>&1; then
    check_pass "AOS 主机可达 (ICMP)"
else
    check_fail "AOS 主机不可达 (ICMP 超时)"
    echo "  可能原因:"
    echo "    - AOS 主机未开机或网络断开"
    echo "    - 防火墙阻止 ICMP"
    echo "    - IP 地址配置错误"
fi
echo ""

echo "【3. TCP 端口连通性测试】"
echo "  测试 TCP $AOS_HOST:$AOS_TCP_PORT ..."
if timeout 5 bash -c "echo >/dev/tcp/$AOS_HOST/$AOS_TCP_PORT" 2>/dev/null; then
    check_pass "TCP 30001 端口开放 (basic_server)"
else
    check_fail "TCP 30001 端口不通"
    echo "  可能原因:"
    echo "    - AOS basic_server 服务未启动"
    echo "    - 防火墙阻止 TCP 30001"
    echo "    - AOS IP 地址配置错误"
fi
echo ""

echo "【4. UDP 端口探测】"
echo "  测试 UDP $AOS_HOST:$AOS_UDP_PORT ..."
if timeout 3 nc -u -z -w 2 "$AOS_HOST" "$AOS_UDP_PORT" 2>/dev/null; then
    check_pass "UDP 30000 端口开放"
else
    check_warn "UDP 30000 端口不通或无响应（非阻断问题）"
fi
echo ""

echo "【5. 服务进程检查】"
echo "  检查本地 M20 服务..."
if systemctl --user status m20-patrol-readonly.service >/dev/null 2>&1; then
    check_pass "m20-patrol-readonly.service 运行中"
else
    check_fail "m20-patrol-readonly.service 未运行"
fi

if pgrep -f "backend.app.server" >/dev/null 2>&1; then
    PID=$(pgrep -f "backend.app.server" | head -1)
    check_pass "Python 服务进程运行中 (PID: $PID)"
else
    check_warn "未发现 Python 服务进程"
fi
echo ""

echo "【6. 端口监听检查】"
echo "  检查 8080 端口..."
if netstat -tlnp 2>/dev/null | grep -q ":8080 "; then
    check_pass "8080 端口正在监听"
    netstat -tlnp 2>/dev/null | grep ":8080 " | sed 's/^/    /'
else
    check_fail "8080 端口未监听"
fi
echo ""

echo "【7. API 健康检查】"
echo "  测试 http://127.0.0.1:8080/api/v1/health ..."
HEALTH=$(curl -s -m 5 http://127.0.0.1:8080/api/v1/health 2>/dev/null || echo "请求失败")
echo "  响应: $HEALTH"
if echo "$HEALTH" | grep -q '"healthy":true'; then
    check_pass "服务健康检查通过"
elif echo "$HEALTH" | grep -q '"healthy":false'; then
    check_warn "服务运行中但健康检查失败（可能TCP未连接）"
else
    check_fail "无法获取健康状态"
fi
echo ""

echo "【8. 状态 API 检查】"
echo "  测试 http://127.0.0.1:8080/api/v1/status/latest ..."
STATUS=$(curl -s -m 5 http://127.0.0.1:8080/api/v1/status/latest 2>/dev/null || echo "请求失败")
echo "  响应: $STATUS"
if echo "$STATUS" | grep -q '"source":"REAL"'; then
    check_pass "已接收到真实数据"
elif echo "$STATUS" | grep -q '"source":"NO_DATA"'; then
    check_fail "无数据（TCP未连接）"
else
    check_warn "状态检查异常"
fi
echo ""

echo "【9. systemd 日志分析】"
echo "  最近 20 条遥测相关日志:"
journalctl --user -u m20-patrol-readonly.service -n 20 --no-pager 2>/dev/null | \
    grep -iE "遥测|连接|心跳|ERROR|timeout" | tail -10 | \
    sed 's/^/    /' || echo "    无相关日志"
echo ""

echo "【10. 网络路由检查】"
echo "  路由表:"
ip route 2>/dev/null | grep -E "10\.21\.31|default" | sed 's/^/    /'
echo ""

echo "【11. DNS/hosts 检查】"
echo "  /etc/hosts 中的 M20 相关条目:"
grep -E "10\.21\.31" /etc/hosts 2>/dev/null | sed 's/^/    /' || echo "    无相关条目"
echo ""

echo "【12. 防火墙检查】"
echo "  iptables 规则（INPUT链）:"
iptables -L INPUT -n 2>/dev/null | head -10 | sed 's/^/    /' || echo "    无法获取防火墙规则"
echo ""

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                         诊断结论                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# 判断主要问题
if ! ping -c 1 -W 1 "$AOS_HOST" >/dev/null 2>&1; then
    echo -e "${RED}主要问题: AOS主机不可达${NC}"
    echo "建议操作:"
    echo "  1. 检查AOS主机(10.21.31.103)是否开机"
    echo "  2. 检查网线连接和交换机状态"
    echo "  3. 确认GOS和AOS在同一网段"
elif ! timeout 5 bash -c "echo >/dev/tcp/$AOS_HOST/$AOS_TCP_PORT" 2>/dev/null; then
    echo -e "${RED}主要问题: TCP 30001端口不通${NC}"
    echo "建议操作:"
    echo "  1. SSH到AOS主机检查basic_server服务"
    echo "  2. 在AOS上执行: ps aux | grep basic"
    echo "  3. 检查AOS防火墙: iptables -L -n | grep 30001"
    echo "  4. 确认AOS IP地址仍为 10.21.31.103"
else
    echo -e "${GREEN}网络连接正常${NC}"
    echo "建议检查:"
    echo "  1. 查看详细日志: journalctl --user -u m20-patrol-readonly.service -f"
    echo "  2. 重启服务: systemctl --user restart m20-patrol-readonly.service"
fi
echo ""

echo "【快速修复命令】"
echo "  # 重启M20服务"
echo "  systemctl --user restart m20-patrol-readonly.service"
echo ""
echo "  # 查看详细日志"
echo "  journalctl --user -u m20-patrol-readonly.service -f"
echo ""
echo "  # 手动测试TCP连接"
echo "  timeout 5 bash -c 'echo | nc -v $AOS_HOST $AOS_TCP_PORT'"
echo ""
