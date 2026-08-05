# 第一阶段架构决策：自主导航、实时状态与双路视频

## 1. 决策摘要

第一阶段在M20 Pro的GOS主机运行巡逻业务系统：

```text
浏览器
  ├─ HTTPS/HTTP：配置、地图、任务
  ├─ WebSocket：实时状态与轨迹
  └─ WebRTC或HLS：前后视频
          │
          ▼
GOS（用户二开主机）
  ├─ Web/API
  ├─ 状态聚合
  ├─ 视频网关
  ├─ 导航安全门控
  └─ 巡逻状态机
      │                  │
      │ TCP 30001        │ 地图只读导出/ROS2（可选）
      ▼                  ▼
AOS basic_server       NOS
10.21.31.103           10.21.31.106
```

- 业务集成首选`basic_server/TCP`，不直接向DDS速度话题发布。
- 前后本体相机通过RTSP获取；浏览器不能原生依赖H.265/RTSP，需GOS转换。
- 地图文件从NOS以只读方式导出到GOS，轨迹来自`1007/2`位置查询；后续可评估`/ODOM`。
- 控制能力默认关闭，导航请求必须经过fail-closed门控。

## 2. 选择basic_server而不是直接DDS的原因

1. 官方定位是业务系统对接与APP开发，协议层相对稳定。
2. TCP提供可靠传输，适合状态订阅和任务下发。
3. 避免外部ROS2版本、DrDDS/FastDDS实现和QoS差异。
4. 官方更新说明指出跨版本ROS2监听曾导致内部ROS2崩溃，并在V1.1.8修复，说明直接DDS需更严格版本约束。
5. GOS可以通过31网段直接访问AOS basic_server，不需要改AOS。

DDS仍可作为第二路径用于高频里程计或点云，但不是第一阶段核心依赖。

## 3. 状态数据流

### 连接与保活

- GOS建立到`10.21.31.103:30001`的TCP长连接。
- 以`Type=100, Command=100`至少1Hz保活。
- 2秒无请求后服务端停止主动上报；3秒无响应，客户端标记断线。
- 使用增量解帧器处理TCP拆包/粘包。

### 状态模型

| 类型/命令 | 频率 | Web用途 |
|---|---:|---|
| 1002/3 | 2Hz/事件 | 异常列表和安全门控 |
| 1002/4 | 10Hz | 姿态、速度、关节与实时仪表 |
| 1002/5 | 2Hz | 电池、温度、CPU、相机/雷达状态 |
| 1002/6 | 2Hz | 模式、步态、急停、充电、版本 |
| 1007/2 | 按需轮询 | 地图位置与轨迹 |
| 2002/1 | 按需轮询 | 定位与避障状态 |
| 1007/1 | 导航期间轮询 | 导航任务状态 |

所有对外Web消息包含：`source`、`received_at`、`age_ms`、`connected`。模拟数据必须明确标识，禁止伪装成真实设备。

## 4. 视频方案

### 已确认源

- `rtsp://10.21.31.103:8554/video1`
- `rtsp://10.21.31.103:8554/video2`
- 默认H.265、1280×720、30fps、单路约1.8Mbps。

### 浏览器显示

浏览器通常不能直接播放RTSP，H.265兼容性也不统一。因此：

- 首选：RTSP/H.265 → GOS硬解/硬编 → WebRTC/H.264。
- 降级：RTSP/H.265 → HLS/H.264，接受更高延迟。
- 禁止默认让每个浏览器各启动一个独立转码器；每路源只保留共享管线。
- 必须实测RK3588硬件编解码、工具版本、CPU/内存和温升后定型。

不要在第一阶段修改AOS的`push_video.sh`，避免影响手柄APP图传。

## 5. 导航任务模型

```text
IDLE
  → PRECHECK
  → DISPATCHING
  → NAVIGATING
  → ARRIVED
  → DWELLING
  → NEXT_POINT / COMPLETED

任意状态
  → CANCELLING
  → CANCELLED

异常/定位丢失/断链
  → PAUSED_REQUIRES_OPERATOR
```

第一版仅允许：

- 任务点`PointInfo=1`；
- 平地敏捷步态，具体协议值按现场软件版本；
- 低速；
- 前进；
- 停避障开启；
- 自主导航；
- 单任务串行。

官方在线指南显示新版本平地/楼梯步态值为`0x3002/0x3003`，旧PDF为`12/13`，属于明确版本冲突。代码必须使用版本化能力表，未经现场版本确认不得下发。

## 6. 版本要求

官方更新说明显示：

- V1.1.7增加ROS2关键状态保护，改变Sleep字段类型，并开放GOS IMU/点云。
- V1.1.8增加全局规划、网络自恢复、模式/步态保护，并修复定位丢失时重复导航、目标点障碍、任务抢占、相机掉线等问题。

建议演示设备升级或确认到V1.1.8，但OTA属于高风险操作，必须由厂商和用户明确批准并备份。若版本低于V1.1.8，应形成差异评估并限制功能。

## 7. 部署策略

- 运行位置：GOS。
- 运行用户：非root。
- CPU：优先绑定4-7大核。
- 配置与代码分离，真实IP/凭据不进入Git。
- 固定Git commit部署，可一键回滚。
- 不在AOS/NOS安装业务依赖，不停止原厂服务。
- 首次部署只启用状态和视频；导航控制在第二次现场放行后启用。

## 8. 现场只读信息采集

在GOS执行：

```bash
printf '\n=== identity ===\n'
hostname
uname -a
cat /etc/os-release

printf '\n=== resources ===\n'
lscpu
free -h
df -h

printf '\n=== network ===\n'
ip -br addr
ip route
ping -c 2 10.21.31.103
ping -c 2 10.21.31.106

printf '\n=== ports ===\n'
nc -zvw3 10.21.31.103 30001
nc -zvw3 10.21.31.103 8554

printf '\n=== runtimes ===\n'
python3 --version
command -v ffmpeg || true
command -v ffprobe || true
command -v gst-launch-1.0 || true
ffmpeg -version 2>/dev/null | sed -n '1,6p'
gst-inspect-1.0 2>/dev/null | grep -Ei 'mpp|rockchip|webrtc|rtsp' | sed -n '1,80p'
```

在NOS执行：

```bash
printf '\n=== version/services ===\n'
systemctl --no-pager --full status localization.service planner.service global_planner.service passable_area.service 2>&1

printf '\n=== active map ===\n'
readlink -f /var/opt/robot/data/maps/active
ls -la /var/opt/robot/data/maps/active
sed -n '1,20p' /var/opt/robot/data/maps/active/occ_grid.yaml

printf '\n=== system version hints ===\n'
grep -RniE 'V1\.1\.[0-9]+|version' /etc/robot /opt/robot /var/opt/robot 2>/dev/null | sed -n '1,120p'
```

这些命令只读取系统信息；如输出含凭据，应先打码。
