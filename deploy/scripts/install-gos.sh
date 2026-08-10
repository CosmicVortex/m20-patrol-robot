#!/usr/bin/env bash
# Simplified install script for direct tar extraction
set -euo pipefail

TARGET_ROOT="$HOME/m20-patrol-robot"
SERVICE_NAME='m20-patrol-readonly.service'
CONFIG_DIR="$HOME/.config/m20-patrol"
DEFAULT_GIMBAL_PASSWORD="m20_gimbal_$(date +%s | sha256sum | head -c 12)"
DEFAULT_ADMIN_PASSWORD="m20_admin_$(date +%s | sha256sum | head -c 12)"
PYTHON_BIN="$(command -v python3)"

echo "=== 安装服务 ==="
echo "目标目录: $TARGET_ROOT"

# 创建目标目录
mkdir -p "$TARGET_ROOT"

# 复制文件
echo "复制文件到 $TARGET_ROOT..."
tar xf /tmp/m20-patrol-robot-deploy.tar.gz -C "$TARGET_ROOT" --strip-components=1

# 编译Python代码
echo "编译Python代码..."
PYTHONPATH="$TARGET_ROOT" python3 -m compileall -q "$TARGET_ROOT/backend"

# 确保配置
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/passwords.env" ]; then
    echo "警告: 未找到密码文件，自动生成默认密码..."
    cat > "$CONFIG_DIR/passwords.env" <<PASSWORDS
export M20_GIMBAL_PASSWORD='$DEFAULT_GIMBAL_PASSWORD'
export M20_ADMIN_PASSWORD='$DEFAULT_ADMIN_PASSWORD'
PASSWORDS
    chmod 600 "$CONFIG_DIR/passwords.env"
    echo "密码已保存到: $CONFIG_DIR/passwords.env"
    echo "M20_GIMBAL_PASSWORD=$DEFAULT_GIMBAL_PASSWORD"
    echo "M20_ADMIN_PASSWORD=$DEFAULT_ADMIN_PASSWORD"
else
    source "$CONFIG_DIR/passwords.env"
fi

echo ""
echo "安装完成 ✅"
echo "运行: bash deploy/scripts/deploy-readonly.sh --start"
