#!/bin/bash
# M20 Pro GOS连接诊断脚本
# 请在GOS主机上执行此脚本

echo "=========================================="
echo "M20 Pro GOS连接诊断"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# 检查网络接口
echo "【1. 本地网络接口】"
ip addr show | grep -E "inet |eth|enp" || ifconfig | grep -E "inet |eth|enp"
echo ""

# 检查AOS可达性
echo "【2. AOS主机 (10.21.31.103) ping测试】"
ping -c 3 10.21.31.103
echo ""

# 检查TCP端口
echo "【3. basic_server TCP端口 (30001) 测试】"
if command -v nc &> /dev/null; then
    nc -zv 10.21.31.103 30001 2>&1
elif command -v telnet &> /dev/null; then
    echo "open 10.21.31.103 30001" | telnet 2>&1 | head -5
else
    echo "未找到nc或telnet命令，尝试Python测试..."
    python3 -c "
import socket
try:
    s = socket.create_connection(('10.21.31.103', 30001), timeout=3)
    print('✅ TCP 30001 连接成功')
    s.close()
except Exception as e:
    print(f'❌ TCP 30001 连接失败: {e}')
"
fi
echo ""

# 检查basic_server服务状态
echo "【4. basic_server服务状态】"
systemctl status basic_server --no-pager 2>/dev/null || echo "basic_server服务不存在或无法访问"
echo ""

# 检查Python服务状态
echo "【5. M20 Web服务状态】"
systemctl status m20-patrol-readonly.service --no-pager 2>/dev/null || \
systemctl status m20-patrol.service --no-pager 2>/dev/null || \
echo "M20 Web服务未运行或无法访问"
echo ""

# 检查最近日志
echo "【6. 最近服务日志】"
journalctl -u m20-patrol-readonly.service --no-pager -n 20 2>/dev/null || \
journalctl -u m20-patrol.service --no-pager -n 20 2>/dev/null || \
cat /var/log/m20-patrol-robot.log 2>/dev/null | tail -20 || \
echo "无法获取日志"
echo ""

# 检查进程
echo "【7. 相关进程】"
ps aux | grep -E "python.*server|basic_server" | grep -v grep
echo ""

# 检查配置文件
echo "【8. 部署配置】"
cat /home/user/m20-patrol-robot/deploy/readonly-manifest.json 2>/dev/null || \
cat ~/m20-patrol-robot/deploy/readonly-manifest.json 2>/dev/null || \
echo "manifest文件未找到"
echo ""

echo "=========================================="
echo "诊断完成"
echo "=========================================="
