#!/usr/bin/env bash
# M20 Pro 一键部署脚本（修复版）
set -euo pipefail

# 检查参数
if [ $# -lt 1 ]; then
    echo "用法: $0 [--verify|--deploy]"
    echo "  --verify  验证环境和连接性"
    echo "  --deploy  执行部署"
    exit 1
fi

ACTION="$1"

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "M20 Pro 巡逻机器人部署脚本"
echo "=========================================="
echo "部署目录: $DEPLOY_DIR"
echo "执行操作: $ACTION"
echo ""

# 检查必要命令
for cmd in python3 bash systemctl; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "错误: 缺少必要命令: $cmd"
        exit 1
    fi
done

# 检查 Python 版本
PYTHON_BIN="$(command -v python3.8 || command -v python3 || true)"
if [ -z "$PYTHON_BIN" ]; then
    echo "错误: 未找到 Python3"
    exit 1
fi

PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')"
echo "Python 版本: $PY_VERSION"

# 验证操作
if [ "$ACTION" = "--verify" ]; then
    echo ""
    echo "=== 环境验证 ==="
    
    # 检查网络连通性
    echo "检查 AOS 连接 (10.21.31.103:30001)..."
    if timeout 5 bash -c 'cat < /dev/null > /dev/tcp/10.21.31.103/30001' 2>/dev/null; then
        echo "  AOS TCP 30001: 可达"
    else
        echo "  警告: AOS TCP 30001 不可达"
    fi
    
    # 检查本地 IP
    echo "本机 IP 地址:"
    ip -4 -o addr show 2>/dev/null | grep -v "127.0.0.1" | awk '{print "  " $4}' | cut -d/ -f1 || hostname -I
    
    echo ""
    echo "=== 验证完成 ==="
    
    # 运行预检
    echo ""
    echo "运行部署预检..."
    bash "$DEPLOY_DIR/deploy/scripts/deploy-readonly.sh" --preflight
fi

# 部署操作
if [ "$ACTION" = "--deploy" ]; then
    echo ""
    echo "=== 开始部署 ==="
    
    # 运行一键部署
    bash "$DEPLOY_DIR/deploy/scripts/deploy-readonly.sh" --one-shot
    
    echo ""
    echo "=== 部署完成 ==="
    echo ""
    echo "验证服务状态:"
    systemctl --user status m20-patrol-readonly.service --no-pager || true
    
    echo ""
    echo "查看实时日志:"
    echo "  journalctl --user -u m20-patrol-readonly.service -f"
    echo ""
    echo "访问 Web UI:"
    echo "  http://10.21.31.104:8080/"
fi

echo ""
echo "部署脚本执行完成"
