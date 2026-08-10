#!/usr/bin/env bash
# M20 Pro 巡逻机器人 - 简化部署脚本
# 自动配置默认密码

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="$ROOT/deploy/readonly-manifest.json"
TARGET_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/m20-patrol-robot"
SERVICE_NAME='m20-patrol-readonly.service'
CONFIG_DIR="$HOME/.config/m20-patrol"

# 确保配置目录存在
ensure_config() {
  mkdir -p "$CONFIG_DIR"
  
  # 如果密码文件不存在，创建默认配置
  if [ ! -f "$CONFIG_DIR/passwords.env" ]; then
    cat > "$CONFIG_DIR/passwords.env" <<EOF
export M20_GIMBAL_PASSWORD="123456"
export M20_ADMIN_PASSWORD="123456"
EOF
    chmod 600 "$CONFIG_DIR/passwords.env"
  fi
  
  # 加载密码
  source "$CONFIG_DIR/passwords.env"
}

# 加载配置
load_manifest() {
  python3 -c "
import json
d = json.load(open('$MANIFEST'))
print('GOS_HOST=' + d['targets']['gos_host'])
print('AOS_HOST=' + d['targets']['aos_host'])
print('NOS_HOST=' + d['targets']['nos_host'])
print('WEB_PORT=' + str(d['ports']['web']))
print('CONTROL_ENABLED=' + str(d['control_enabled']).lower())
print('TELEMETRY_TX_ENABLED=' + str(d['telemetry_tx_enabled']).lower())
print('STALE_AFTER_SECONDS=' + str(d['stale_after_seconds']))
"
}

# 预检（简化）
preflight() {
  echo "=== 预检 ==="
  
  # 确保配置
  ensure_config
  
  echo "GIMBAL_PASSWORD=$M20_GIMBAL_PASSWORD"
  echo "ADMIN_PASSWORD=$M20_ADMIN_PASSWORD"
  echo ""
  
  # 检查Python
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 未找到"
    exit 1
  fi
  echo "Python: $(python3 --version 2>&1)"
  
  # 检查systemd
  if ! command -v systemctl >/dev/null 2>&1; then
    echo "ERROR: systemctl 未找到"
    exit 1
  fi
  echo "systemd: 可用"
  
  # 检查目标目录
  mkdir -p "$TARGET_ROOT"
  echo "目标目录: $TARGET_ROOT"
  
  # 检查配置文件
  if [ ! -f "$MANIFEST" ]; then
    echo "ERROR: 部署清单文件未找到: $MANIFEST"
    exit 1
  fi
  echo "配置: 已加载"
  
  # 加载配置
  eval "$(load_manifest)"
  echo "GOS_HOST=$GOS_HOST"
  echo "AOS_HOST=$AOS_HOST"
  echo "NOS_HOST=$NOS_HOST"
  echo "WEB_PORT=$WEB_PORT"
  
  # 检查磁盘空间
  echo ""
  echo "磁盘空间:"
  df -h "$TARGET_ROOT" 2>/dev/null || df -h ~ 2>/dev/null || true
  
  echo ""
  echo "预检完成 ✅"
}

# 安装服务
install() {
  echo "=== 安装服务 ==="
  
  # 确保配置
  ensure_config
  
  # 加载配置
  eval "$(load_manifest)"
  
  # 创建目标目录
  mkdir -p "$TARGET_ROOT"
  
  # 复制文件（排除目标目录本身，避免递归复制）
  echo "复制文件到 $TARGET_ROOT..."
  
  # 使用rsync或直接复制文件
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --exclude='.local' "$ROOT/" "$TARGET_ROOT/"
  else
    # 复制所有文件，但排除目标目录
    find "$ROOT" -mindepth 1 -maxdepth 1 -exec cp -r {} "$TARGET_ROOT/" \;
    # 确保不复制目标目录本身
    rm -rf "$TARGET_ROOT/.local/share/m20-patrol-robot" 2>/dev/null || true
  fi
  
  # 创建虚拟环境
  echo "创建Python虚拟环境..."
  python3 -m venv --system-site-packages "$TARGET_ROOT/.venv"
  
  # 编译Python代码
  echo "编译Python代码..."
  PYTHONPATH="$TARGET_ROOT" "$TARGET_ROOT/.venv/bin/python" -m compileall -q "$TARGET_ROOT/backend"
  
  # 准备systemd服务文件
  echo "准备systemd服务文件..."
  UNIT_PATH="$HOME/.config/systemd/user/$SERVICE_NAME"
  mkdir -p "$(dirname "$UNIT_PATH")"
  
  # 替换模板变量
  sed -e "s#@GOS_HOST@#$GOS_HOST#g" \
      -e "s#@AOS_HOST@#$AOS_HOST#g" \
      -e "s#@NOS_HOST@#$NOS_HOST#g" \
      -e "s#@WEB_PORT@#$WEB_PORT#g" \
      -e "s#@STALE_AFTER_SECONDS@#$STALE_AFTER_SECONDS#g" \
      "$ROOT/deploy/systemd/m20-patrol-readonly.service" > "$UNIT_PATH"
  
  # 重新加载systemd
  echo "重新加载systemd..."
  systemctl --user daemon-reload
  
  echo ""
  echo "安装完成 ✅"
  echo ""
  echo "配置信息:"
  echo "  服务: $SERVICE_NAME"
  echo "  地址: http://$GOS_HOST:$WEB_PORT"
  echo "  用户名: admin"
  echo "  密码: $M20_ADMIN_PASSWORD"
  echo "  密码文件: $CONFIG_DIR/passwords.env"
}

# 启动服务
start() {
  echo "=== 启动服务 ==="
  systemctl --user start "$SERVICE_NAME"
  echo "服务启动请求已发送 ✅"
}

# 查看状态
status() {
  echo "=== 服务状态 ==="
  systemctl --user status "$SERVICE_NAME" --no-pager
}

# 停止服务
stop() {
  echo "=== 停止服务 ==="
  systemctl --user stop "$SERVICE_NAME"
  echo "服务已停止 ✅"
}

# 重启服务
restart() {
  echo "=== 重启服务 ==="
  systemctl --user restart "$SERVICE_NAME"
  echo "服务已重启 ✅"
}

# 查看日志
logs() {
  echo "=== 服务日志 ==="
  journalctl --user -u "$SERVICE_NAME" -f
}

# 显示密码
show-passwords() {
  ensure_config
  echo "=== 已保存的密码 ==="
  echo "M20_GIMBAL_PASSWORD=$M20_GIMBAL_PASSWORD"
  echo "M20_ADMIN_PASSWORD=$M20_ADMIN_PASSWORD"
}

# 主入口
case "${1:---one-shot}" in
  --preflight) preflight ;;
  --install) install ;;
  --start) start ;;
  --status) status ;;
  --stop) stop ;;
  --restart) restart ;;
  --logs) logs ;;
  --show-passwords) show-passwords ;;
  --one-shot) preflight; install; start; status ;;
  *) echo "用法: $0 {--preflight|--install|--start|--status|--stop|--restart|--logs|--show-passwords|--one-shot}" ;;
esac
