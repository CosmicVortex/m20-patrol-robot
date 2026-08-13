#!/bin/bash
# M20 Pro 快速诊断脚本 - 在GOS上运行
# 检查telemetry连接状态

echo "=========================================="
echo "M20 Pro 连接诊断"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# 检查Python进程
echo "【1. 检查Python进程】"
ps aux | grep "python.*server" | grep -v grep || echo "未找到Python进程"
echo ""

# 检查日志
echo "【2. 检查最近日志】"
journalctl --user -u m20-patrol-readonly.service --no-pager -n 20 2>/dev/null || \
tail -20 /home/user/m20-patrol-robot/*.log 2>/dev/null || \
echo "无日志文件"
echo ""

# 测试API
echo "【3. 测试API响应】"
curl -s http://localhost:8080/api/v1/status 2>/dev/null | python3 -m json.tool 2>/dev/null || \
curl -s http://10.21.31.104:8080/api/v1/status 2>/dev/null | python3 -m json.tool 2>/dev/null || \
echo "API无响应"
echo ""

# 测试TCP连接
echo "【4. 测试TCP连接到AOS】"
python3 -c "
import socket
try:
    s = socket.create_connection(('10.21.31.103', 30001), timeout=3)
    print('✅ TCP 30001 连接成功')
    s.close()
except Exception as e:
    print(f'❌ TCP 30001 连接失败: {e}')
"
echo ""

# 检查manifest配置
echo "【5. 检查配置】"
cat ~/m20-patrol-robot/deploy/readonly-manifest.json 2>/dev/null | python3 -m json.tool 2>/dev/null || \
echo "无法读取manifest"
echo ""

echo "=========================================="
echo "诊断完成"
echo "=========================================="
