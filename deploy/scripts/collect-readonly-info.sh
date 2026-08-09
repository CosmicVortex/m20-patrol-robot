# 第一阶段现场只读采集脚本
# 用法：仅在固定现场地址上执行，不扫描或猜测目标地址。
# 示例：AOS_HOST=10.21.31.103 GOS_HOST=10.21.31.104 NOS_HOST=10.21.31.106 bash collect-readonly-info.sh
# 本脚本不发布ROS2消息，不发送basic_server报文，不修改配置或服务。

set -u

require_ipv4() {
  local name="$1" value="${!1:-}" part
  local -a parts
  if [ -z "$value" ]; then
    printf 'ERROR: %s must be a field-approved IPv4 address; refusing candidate probing\n' "$name" >&2
    exit 2
  fi
  if ! [[ "$value" =~ ^(0|[1-9][0-9]{0,2})\.(0|[1-9][0-9]{0,2})\.(0|[1-9][0-9]{0,2})\.(0|[1-9][0-9]{0,2})$ ]]; then
    printf 'ERROR: %s must use canonical dotted-decimal IPv4 notation\n' "$name" >&2
    exit 2
  fi
  IFS='.' read -r -a parts <<< "$value"
  for part in "${parts[@]}"; do
    if ((10#$part > 255)); then
      printf 'ERROR: %s is not an IPv4 address\n' "$name" >&2
      exit 2
    fi
  done
  # Field targets must be ordinary unicast hosts. Do not probe unspecified,
  # broadcast, multicast, loopback, or link-local addresses.
  # The approved field subnet mask is not supplied to this script. Fail closed
  # for addresses that are network or directed-broadcast candidates under the
  # common /24 allocation used by the documented robot LAN.
  if [ "${parts[3]}" = "0" ] || [ "${parts[3]}" = "255" ]; then
    printf 'ERROR: %s must not be a network or directed-broadcast candidate\n' "$name" >&2
    exit 2
  fi
  if [ "$value" = "255.255.255.255" ] \
    || ((10#${parts[0]} == 0)) \
    || ((10#${parts[0]} >= 224)) \
    || ((10#${parts[0]} == 127)) \
    || [ "${parts[0]}.${parts[1]}" = "169.254" ]; then
    printf 'ERROR: %s must be an approved unicast host address\n' "$name" >&2
    exit 2
  fi
}

require_ipv4 AOS_HOST
require_ipv4 GOS_HOST
require_ipv4 NOS_HOST

printf '\n===== EXECUTION CONTEXT =====\n'
date -Is
hostname
whoami
uname -a
cat /etc/os-release 2>/dev/null || true

printf '\n===== RESOURCES =====\n'
lscpu 2>/dev/null || true
free -h 2>/dev/null || true
df -h 2>/dev/null || true

printf '\n===== NETWORK =====\n'
printf 'Approved AOS_HOST=%s GOS_HOST=%s NOS_HOST=%s\n' "$AOS_HOST" "$GOS_HOST" "$NOS_HOST"
ip -br addr 2>/dev/null || true
ip route 2>/dev/null || true
ping -c 2 -W 1 "$AOS_HOST" 2>&1 || true
ping -c 2 -W 1 "$GOS_HOST" 2>&1 || true
ping -c 2 -W 1 "$NOS_HOST" 2>&1 || true

printf '\n===== DOCUMENTED PORTS =====\n'
if command -v nc >/dev/null 2>&1; then
  nc -zvw3 "$AOS_HOST" 30001 2>&1 || true
  nc -zvw3 "$AOS_HOST" 8554 2>&1 || true
else
  timeout 3 bash -c "</dev/tcp/$AOS_HOST/30001" 2>&1 && echo 'TCP 30001 reachable' || true
  timeout 3 bash -c "</dev/tcp/$AOS_HOST/8554" 2>&1 && echo 'TCP 8554 reachable' || true
fi

printf '\n===== RUNTIMES =====\n'
python3 --version 2>&1 || true
command -v ffmpeg || true
command -v ffprobe || true
command -v gst-launch-1.0 || true
ffmpeg -version 2>/dev/null | sed -n '1,8p' || true
gst-inspect-1.0 2>/dev/null | grep -Ei 'mpp|rockchip|webrtc|rtsp|h264|h265' | sed -n '1,120p' || true

printf '\n===== ROS ENVIRONMENT (READ ONLY) =====\n'
test -f /opt/ros/foxy/setup.bash && echo 'ROS Foxy setup exists' || true
printenv | grep -E '^ROS|^RMW|^FAST|^CYCLONE' | sort || true

printf '\n===== RELEVANT SERVICES (READ ONLY) =====\n'
for svc in localization planner global_planner passable_area rsdriver_node rl_deploy basic_server; do
  systemctl is-active "$svc.service" 2>&1 | sed "s/^/$svc: /" || true
done

printf '\n===== ACTIVE MAP (NOS EXPECTED) =====\n'
readlink -f /var/opt/robot/data/maps/active 2>&1 || true
stat /var/opt/robot/data/maps/active/occ_grid.pgm 2>&1 || true
sed -n '1,20p' /var/opt/robot/data/maps/active/occ_grid.yaml 2>&1 || true

printf '\n===== VERSION HINTS =====\n'
for f in /etc/robot/version /opt/robot/version /var/opt/robot/version /etc/os-release; do
  if [ -f "$f" ]; then
    printf '\n--- %s ---\n' "$f"
    sed -n '1,80p' "$f"
  fi
done

printf '\n===== END =====\n'
