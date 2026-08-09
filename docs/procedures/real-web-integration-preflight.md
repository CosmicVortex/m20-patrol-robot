# M20 Pro 真实 Web 联调前置采集

**用途：** 在用户本地笔记本或 M20 GOS 执行，采集真实接口、版本、视频和安全门证据。  
**执行边界：** 只读；不发送 basic_server 报文，不发布 ROS2/DDS，不修改服务/配置，不启动导航，不发送运动控制。

## 一、执行环境

```bash
set -u
printf '\n===== CONTEXT =====\n'
date -Is
hostname
whoami
uname -a
python3 --version 2>&1 || true
printf '\n===== ROBOT VERSION =====\n'
for f in /etc/robot/version /opt/robot/version /var/opt/robot/version; do
  if [ -f "$f" ]; then printf '\n--- %s ---\n' "$f"; sed -n '1,120p' "$f"; fi
done
printf '\n===== SERVICES =====\n'
for svc in basic_server localization planner global_planner passable_area rl_deploy; do
  systemctl is-active "$svc.service" 2>&1 | sed "s/^/$svc: /" || true
done
```

## 二、目标连通性

仅使用负责人确认地址：

```bash
AOS_HOST=10.21.31.103
GOS_HOST=10.21.31.104
NOS_HOST=10.21.31.106

printf '\n===== NETWORK =====\n'
ping -c 2 -W 1 "$AOS_HOST" 2>&1 || true
ping -c 2 -W 1 "$NOS_HOST" 2>&1 || true

printf '\n===== TCP PORTS =====\n'
for port in 30001 8554; do
  timeout 3 bash -c "</dev/tcp/$AOS_HOST/$port" 2>&1 \
    && printf 'TCP %s OPEN\n' "$port" \
    || printf 'TCP %s CLOSED_OR_UNREACHABLE\n' "$port"
done
```

## 三、协议服务只读证据

如果现场已有只读采集脚本，优先执行仓库脚本：

```bash
AOS_HOST=10.21.31.103 GOS_HOST=10.21.31.104 NOS_HOST=10.21.31.106 \
bash deploy/scripts/collect-readonly-info.sh
```

返回完整原始输出。不要截断、不要手工改写、不要把离线模拟输出当作现场输出。

## 四、视频只读探测

仅在现场确认 RTSP 地址后执行。若地址未确认，不得猜测或执行：

```bash
command -v ffprobe || true
ffprobe -v error -rtsp_transport tcp \
  -show_entries stream=codec_name,width,height,r_frame_rate \
  -of json 'RTSP_URL_FROM_FIELD_CONFIRMATION'
```

请返回：

- RTSP URL（可遮蔽密码，但保留主机、端口、路径）
- ffprobe 完整 JSON 输出
- 是否需要账号密码
- 是否允许服务端转为浏览器可播放格式
- 截图/录像保存目录和保留期限

## 五、控制放行材料（不要在未确认前执行）

真实导航/运动接口尚不能仅凭云端代码启用。启用前必须取得负责人确认：

- 现场机器人确认为 M20 Pro
- 现场软件/固件版本
- 《软件开发指南》V1.2.1 适用性确认
- AOS basic_server TCP/UDP 端口和协议权限
- 定位正常
- 避障/停障正常
- 急停可用
- 无活动导航任务
- 电量满足现场放行阈值
- 明确安全区域、观察员和回滚/断电方案
- 负责人姓名、时间和授权事项

## 六、账户与数据管理前置确认

请确认：

- 初始管理员创建方式
- 账户角色：管理员、操作员、观察员、维护员
- 密码复杂度、会话时长、失败锁定策略
- 审计日志保留时长
- 视频、截图、录像和报告存储位置
- 数据导出权限与删除权限
- 是否允许云端 Web 仅通过 GOS 反向代理访问

## 七、返回格式

请将以上命令的完整真实输出直接返回，并标注：

- `HOST_EXECUTION=笔记本` 或 `HOST_EXECUTION=GOS`
- `OUTPUT_COMPLETE=true/false`
- `CONTROL_AUTHORIZATION=未授权/已授权`
- `VIDEO_EVIDENCE=未提供/已提供`
- `ACCOUNT_POLICY=未确认/已确认`
