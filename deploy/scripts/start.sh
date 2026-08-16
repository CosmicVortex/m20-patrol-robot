#!/bin/bash
# M20 Pro 巡逻机器人系统 - 一键启动脚本
# 用法: ./start.sh
#
# 部署说明参考: docs/项目文档/05-部署说明.md

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "M20 Pro 巡逻机器人系统"
echo "========================================"
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3"
    exit 1
fi

echo "✅ Python环境: $(python3 --version)"
echo ""

# 加载密码配置文件（如存在）
CONFIG_DIR="$HOME/.config/m20-patrol"
if [ -f "$CONFIG_DIR/passwords.env" ]; then
    source "$CONFIG_DIR/passwords.env"
    echo "✅ 已加载密码配置: $CONFIG_DIR/passwords.env"
else
    echo "⚠️  未找到密码配置文件，使用默认密码"
    export M20_GIMBAL_PASSWORD="123456"
    export M20_ADMIN_PASSWORD="123456"
fi
echo ""

# 设置运行时环境变量
export M20_RUNTIME_MODE="${M20_RUNTIME_MODE:-realtime_readonly}"
export M20_READ_ONLY_MODE="${M20_READ_ONLY_MODE:-true}"
export M20_CONTROL_ENABLED="${M20_CONTROL_ENABLED:-false}"
export M20_TELEMETRY_TX_ENABLED="${M20_TELEMETRY_TX_ENABLED:-false}"
export M20_TELEMETRY_RX_ENABLED="${M20_TELEMETRY_RX_ENABLED:-true}"
export M20_STALE_AFTER_SECONDS="${M20_STALE_AFTER_SECONDS:-3}"

echo "🚀 启动 M20 Web 服务..."
echo ""
echo "运行时配置:"
echo "  模式: $M20_RUNTIME_MODE"
echo "  只读: $M20_READ_ONLY_MODE"
echo "  控制: $M20_CONTROL_ENABLED"
echo ""

exec python3 backend/app/server.py "$@"

