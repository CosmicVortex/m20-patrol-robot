#!/usr/bin/env bash
# M20 Pro 巡逻机器人 - 简化部署脚本（离线版）
# 直接使用系统Python，无需虚拟环境

set -euo pipefail

# 检测脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 找到项目根目录
# 结构: ROOT/deploy/scripts/deploy-readonly.sh
# 所以 ROOT = SCRIPT_DIR 的上级目录的上级目录
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

MANIFEST="$ROOT/deploy/readonly-manifest.json"
TARGET_ROOT="$HOME/m20-patrol-robot"
SERVICE_NAME='m20-patrol-readonly.service'
# 密码文件路径
CONFIG_DIR="$HOME/.config/m20-patrol"
# 项目负责人确认的首次部署默认密码。现场验收后应立即修改。
DEFAULT_GIMBAL_PASSWORD="123456"
DEFAULT_ADMIN_PASSWORD="123456"
PYTHON_BIN="$(command -v python3)"
FFMPEG_BIN=""

# 检查是否为root用户
check_root() {
  if [ "$(id -u)" -eq 0 ]; then
    echo "ERROR: 不允许使用root用户部署"
    echo "请使用普通用户运行: bash deploy/scripts/deploy-readonly.sh --one-shot"
    exit 1
  fi
}

# 检查Python环境
check_python() {
  echo "检查Python环境..."
  
  if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 未找到"
    exit 1
  fi
  
  PYTHON_VERSION=$(python3 --version 2>&1)
  echo "Python: $PYTHON_VERSION"
  case "$PYTHON_VERSION" in
    "Python 3.8.10"*) ;;
    *) echo "错误: GOS必须使用Python 3.8.10，当前为 $PYTHON_VERSION"; exit 1 ;;
  esac
  # GOS离线环境禁止依赖虚拟环境；同时确认venv和ensurepip不可用/不被部署依赖。
  python3 -c "import asyncio, json, ssl, urllib, email, logging" 2>/dev/null || {
    echo "错误: Python缺少必要标准库模块"
    exit 1
  }
  python3 -c "import venv, ensurepip" >/dev/null 2>&1 || {
    echo "提示: venv或ensurepip不可用，按系统Python部署，不创建虚拟环境"
  }
  
  echo "Python环境检查通过 ✅"
}

# 确保配置目录存在
check_ffmpeg() {
  echo "检查FFmpeg环境..."
  case "$(uname -m)" in
    aarch64|arm64) ;;
    *) echo "错误: GOS架构必须为aarch64/arm64，当前为 $(uname -m)"; exit 1 ;;
  esac

  # 遍历所有候选 ffmpeg，选择第一个支持 RTSP 的版本
  local _candidate _has_demux _has_proto _selected_bin=""
  echo "查找支持 RTSP 的 FFmpeg..."
  for _candidate in /usr/bin/ffmpeg "$HOME/.local/bin/ffmpeg" "/opt/m20-ffmpeg/bin/ffmpeg"; do
    [ -x "$_candidate" ] || continue
    echo "  检查: $_candidate"

    # 测试 RTSP 能力：demuxer 含 rtsp + 传输层含 tcp/udp
    _has_demux=false
    _has_proto=false
    # 使用 awk 提取第二列并精确匹配，避免 tr 转义问题
    if "$_candidate" -hide_banner -demuxers 2>/dev/null | awk '{print $2}' | grep -qx rtsp; then
      _has_demux=true
    fi
    "$_candidate" -hide_banner -protocols 2>/dev/null | grep -qwE 'tcp|udp' && _has_proto=true

    echo "    demuxer: $([ "$_has_demux" = true ] && echo 'rtsp ✓' || echo 'rtsp ✗')"
    echo "    protocol: $([ "$_has_proto" = true ] && echo 'tcp/udp ✓' || echo 'tcp/udp ✗')"

    if [ "$_has_demux" = true ] && [ "$_has_proto" = true ]; then
      _selected_bin="$_candidate"
      echo "  选择: $_candidate ✓"
      break
    else
      echo "  跳过: $_candidate"
    fi
  done

  if [ -z "$_selected_bin" ]; then
    echo "错误: 所有已安装的 FFmpeg 均不支持 RTSP"
    echo "  请执行: bash deploy/offline/ffmpeg/install-ffmpeg-offline.sh"
    exit 1
  fi

  # 验证 ffprobe 存在（与选中的 ffmpeg 同目录）
  local _ffprobe_bin
  _ffprobe_bin="$(dirname "$_selected_bin")/ffprobe"
  if [ ! -x "$_ffprobe_bin" ] && ! command -v ffprobe >/dev/null 2>&1; then
    echo "错误: 未找到 ffprobe。请安装完整 FFmpeg 离线包"
    exit 1
  fi

  # 输出选中的版本信息
  echo "使用 FFmpeg: $_selected_bin"
  "$_selected_bin" -version 2>/dev/null | sed -n '1,2p'
  echo "FFmpeg环境检查通过 ✅"

  # 导出全局变量供后续使用
  FFMPEG_BIN="$_selected_bin"
}

# 确保配置目录存在
ensure_config() {
  # 创建配置目录并设置严格权限（仅所有者可读写执行）
  mkdir -p -m 700 "$CONFIG_DIR"

  if [ ! -f "$CONFIG_DIR/passwords.env" ]; then
    echo "警告: 未找到密码文件，自动生成默认密码..."
    cat > "$CONFIG_DIR/passwords.env" <<EOF
M20_GIMBAL_PASSWORD='$DEFAULT_GIMBAL_PASSWORD'
M20_ADMIN_PASSWORD='$DEFAULT_ADMIN_PASSWORD'
EOF
    chmod 600 "$CONFIG_DIR/passwords.env"
    source "$CONFIG_DIR/passwords.env"
    echo "密码已保存到: $CONFIG_DIR/passwords.env"
  else
    # 校验并修正已有密码文件的权限
    local _perms
    _perms=$(stat -c '%a' "$CONFIG_DIR/passwords.env" 2>/dev/null || stat -f '%Lp' "$CONFIG_DIR/passwords.env" 2>/dev/null || echo "unknown")
    if [ "$_perms" != "600" ] && [ "$_perms" != "unknown" ]; then
      echo "警告: 密码文件权限为 $_perms，应修正为 600"
      chmod 600 "$CONFIG_DIR/passwords.env"
    fi
    # 加载密码
    source "$CONFIG_DIR/passwords.env"
  fi
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
print('AOS_TCP_PORT=' + str(d['ports']['aos_tcp']))
print('CONTROL_ENABLED=' + str(d['control_enabled']).lower())
print('TELEMETRY_TX_ENABLED=' + str(d['telemetry_tx_enabled']).lower())
print('STALE_AFTER_SECONDS=' + str(d['stale_after_seconds']))
"
}

# 预检
preflight() {
  echo "=== 预检 ==="
  
  # 检查root
  check_root
  
  check_python
  check_ffmpeg
  
  # 确保配置
  ensure_config
  
  echo "密码文件已加载: $CONFIG_DIR/passwords.env（权限应为0600）"
  
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
  echo "AOS_TCP_PORT=$AOS_TCP_PORT"
  
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
  
  # 复制文件（如果已在目标目录，跳过复制）
  echo "复制文件到 $TARGET_ROOT..."
  
  if [ "$ROOT" != "$TARGET_ROOT" ]; then
    (cd "$ROOT" && tar cf - --exclude='__pycache__' --exclude='.git' .) | (cd "$TARGET_ROOT" && tar xf -)
  else
    echo "已在目标目录，跳过复制"
  fi

  for asset in \
    "$TARGET_ROOT/docs/website/index.html" \
    "$TARGET_ROOT/docs/website/js/app.js" \
    "$TARGET_ROOT/docs/website/js/views/dashboard.js" \
    "$TARGET_ROOT/docs/website/robot-dog.png" \
    "$TARGET_ROOT/docs/website/robot-dog.jpg"; do
    if [ ! -f "$asset" ]; then
      echo "错误: Web 资源缺失: $asset"
      exit 1
    fi
  done
  echo "Web 资源校验通过"
  
  # 编译Python代码
  echo "编译Python代码..."
  PYTHONPATH="$TARGET_ROOT" python3 -m compileall -q "$TARGET_ROOT/backend"
  
  # 准备systemd服务文件
  echo "准备systemd服务文件..."
  UNIT_PATH="$HOME/.config/systemd/user/$SERVICE_NAME"
  mkdir -p "$(dirname "$UNIT_PATH")"
  
  # 生成服务文件（直接替换所有变量）
  cat > "$UNIT_PATH" <<EOF
[Unit]
Description=M20 Patrol Robot read-only dashboard
After=network.target

[Service]
Type=simple
WorkingDirectory=${TARGET_ROOT}
Environment=PYTHONPATH=${TARGET_ROOT}
Environment=PATH=%h/.local/bin:/usr/local/bin:/usr/bin:/bin
EnvironmentFile=${CONFIG_DIR}/passwords.env
Environment=M20_RUNTIME_MODE=realtime_readonly
Environment=M20_READ_ONLY_MODE=true
Environment=M20_CONTROL_ENABLED=false
Environment=M20_TELEMETRY_TX_ENABLED=false
Environment=M20_TARGET_HOST=${AOS_HOST}
Environment=M20_TARGET_PORT=${AOS_TCP_PORT}
Environment=M20_TELEMETRY_RX_ENABLED=true
Environment=M20_WEB_REALTIME_ENABLED=true
Environment=M20_STALE_AFTER_SECONDS=${STALE_AFTER_SECONDS}
ExecStart=${PYTHON_BIN} -m backend.app.server --manifest ${TARGET_ROOT}/deploy/readonly-manifest.json
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${TARGET_ROOT}
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6

[Install]
WantedBy=default.target
EOF
  
  # 重新加载systemd
  echo "重新加载systemd..."
  systemctl --user daemon-reload
  
  echo ""
  echo "安装完成 ✅"
  echo ""
  echo "配置信息:"
  echo "  服务: $SERVICE_NAME"
  echo "  地址: http://${GOS_HOST}:${WEB_PORT}"
  echo "  用户名: admin"
  echo "  密码: 已写入受限权限文件"
  echo "  密码文件: $CONFIG_DIR/passwords.env（权限应为0600）"
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
  echo "密码文件路径: $CONFIG_DIR/passwords.env"
  echo "如需查看或修改，请在本地受控终端操作。"
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
