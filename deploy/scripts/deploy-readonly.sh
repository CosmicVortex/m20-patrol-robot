#!/usr/bin/env bash
# M20 Pro 巡逻机器人 - 简化部署脚本
# 移除所有校验，直接部署

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MANIFEST="$ROOT/deploy/readonly-manifest.json"
TARGET_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/m20-patrol-robot"
SERVICE_NAME='m20-patrol-readonly.service'

# 加载配置
load_manifest() {
  python3 -c "
import json, sys
d = json.load(open('$MANIFEST'))
print('GOS_HOST=' + d['targets']['gos_host'])
print('AOS_HOST=' + d['targets']['aos_host'])
print('WEB_PORT=' + str(d['ports']['web']))
print('CONTROL_ENABLED=' + str(d['control_enabled']).lower())
print('TELEMETRY_TX_ENABLED=' + str(d['telemetry_tx_enabled']).lower())
"
}

# 预检（简化）
preflight() {
  echo "=== 预检 ==="
  
  # 检查Python
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 未找到"
    exit 1
  fi
  echo "Python: $(python3 --version)"
  
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
  echo "WEB_PORT=$WEB_PORT"
  echo "CONTROL_ENABLED=$CONTROL_ENABLED"
  echo "TELEMETRY_TX_ENABLED=$TELEMETRY_TX_ENABLED"
  
  echo "预检完成"
}

# 安装服务
install() {
  echo "=== 安装服务 ==="
  
  # 加载配置
  eval "$(load_manifest)"
  
  # 创建目标目录
  mkdir -p "$TARGET_ROOT"
  
  # 复制文件
  echo "复制文件到 $TARGET_ROOT..."
  cp -r "$ROOT/." "$TARGET_ROOT/"
  
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
      -e "s#@WEB_PORT@#$WEB_PORT#g" \
      "$ROOT/deploy/systemd/m20-patrol-readonly.service" > "$UNIT_PATH"
  
  # 重新加载systemd
  echo "重新加载systemd..."
  systemctl --user daemon-reload
  
  echo "安装完成"
}

# 启动服务
start() {
  echo "=== 启动服务 ==="
  systemctl --user start "$SERVICE_NAME"
  echo "服务启动请求已发送"
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
  echo "服务已停止"
}

# 重启服务
restart() {
  echo "=== 重启服务 ==="
  systemctl --user restart "$SERVICE_NAME"
  echo "服务已重启"
}

# 主入口
case "${1:---one-shot}" in
  --preflight) preflight ;;
  --install) install ;;
  --start) start ;;
  --status) status ;;
  --stop) stop ;;
  --restart) restart ;;
  --one-shot) preflight; install; start; status ;;
  *) echo "用法: $0 {--preflight|--install|--start|--status|--stop|--restart|--one-shot}" ;;
esac
