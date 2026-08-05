# 第一阶段现场只读采集脚本
# 用法：分别在GOS与NOS执行相应章节，将完整输出保存并返回。
# 本脚本不发布ROS2消息，不发送basic_server报文，不修改配置或服务。

set -u

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
ip -br addr 2>/dev/null || true
ip route 2>/dev/null || true
ping -c 2 -W 1 10.21.31.103 2>&1 || true
ping -c 2 -W 1 10.21.31.106 2>&1 || true
ping -c 2 -W 1 10.21.31.104 2>&1 || true

printf '\n===== DOCUMENTED PORTS =====\n'
if command -v nc >/dev/null 2>&1; then
  nc -zvw3 10.21.31.103 30001 2>&1 || true
  nc -zvw3 10.21.31.103 8554 2>&1 || true
else
  timeout 3 bash -c '</dev/tcp/10.21.31.103/30001' 2>&1 && echo 'TCP 30001 reachable' || true
  timeout 3 bash -c '</dev/tcp/10.21.31.103/8554' 2>&1 && echo 'TCP 8554 reachable' || true
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
