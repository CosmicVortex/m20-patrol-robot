# 第一阶段：自主导航与 Web 实时监控实施计划

> **For Hermes:** 后续按严格 TDD 分任务实施。所有机器人控制能力默认禁用，只有现场安全放行后才允许启用。

**目标：** 在 M20 Pro 的 GOS（10.21.31.104，地址仍需现场确认）部署一个本地 Web 系统，实现机器人实时状态、地图轨迹、前后广角相机视频显示，以及经过安全门控的单点/多点自主导航。

**总体架构：** GOS 运行 Python 后端与 Web 前端。后端通过 AOS `basic_server` TCP 30001 获取状态、位置和导航结果；通过 RTSP读取本体前后相机；浏览器只连接 GOS 的 HTTP/WebSocket/WebRTC/HLS 服务，不直接访问 AOS。自主导航由后端状态机串行下发，默认处于只读模式。

**技术栈建议：** Python 3 标准库优先；FastAPI/uvicorn（现场确认后离线安装）；pytest；前端采用轻量 TypeScript/Vite 或无构建原生模块；FFmpeg/GStreamer负责RTSP转浏览器格式。部署目标为ARM64 RK3588、Ubuntu 20.04。

---

## 1. 已确认的官方接口事实

- AOS：`10.21.31.103`；运行 `basic_server` 与运控。
- NOS：`10.21.31.106`；负责地图、定位、规划和避障。
- GOS：`10.21.31.104`；官方建议用户二开优先部署于GOS。
- `basic_server`：UDP `30000`，TCP `30001`；TCP推荐任务下发和状态订阅。
- TCP连接建立后主动接收状态；客户端应至少1Hz保活；服务端2秒无请求停止主动推送；客户端3秒无响应应判定断线。
- 状态上报：`1002/3`异常2Hz，`1002/4`运控10Hz，`1002/5`设备2Hz，`1002/6`基础2Hz。
- 位姿：`1007/2`；定位/感知状态：`2002/1`。
- 导航：`1003/1`下发单点；`1004/1`取消；`1007/1`查询状态。仅M20 Pro支持。
- 前相机：`rtsp://10.21.31.103:8554/video1`；后相机：`rtsp://10.21.31.103:8554/video2`。
- 本体相机默认H.265、1280×720、30fps、约1.8Mbps；相机不发布DDS话题。
- 地图位于NOS `/var/opt/robot/data/maps/active`；包含`occ_grid.pgm`、`occ_grid.yaml`。
- GOS为RK3588 ARM64、16GB内存、128GB eMMC；二开进程建议绑定CPU 4-7。

以上地址和版本均为文档事实，部署前必须由现场命令确认。

## 2. 必须采用的安全边界

1. `ROBOT_CONTROL_ENABLED=false`为默认值。
2. Web API无任何直接速度/轴控制接口。
3. 导航启动前必须同时满足：
   - 型号返回`PRO`；
   - 设备版本完成兼容性确认，优先要求V1.1.8或厂商认可版本；
   - 硬急停未触发；
   - 定位状态正常；
   - 无保护级异常；
   - 电量满足现场阈值（建议≥30%，不得低于厂商20%失败阈值）；
   - 当前无导航任务；
   - 地图ID和点位属于当前激活地图；
   - 操作员已完成一次性现场解锁；
   - Web请求携带幂等键并通过角色鉴权。
4. 定位丢失、basic_server断链、硬急停、保护异常、低电量或任务超时，系统必须停止继续派发点位，并进入人工确认状态。
5. 第一轮实机测试只允许空旷平地、低速、自主导航、平地步态和一个目标点；不测试楼梯、高台、倒退或关闭停避障。
6. 不修改AOS脚本和原厂服务；视频参数先只读使用默认值。

## 3. 目标软件结构

```text
backend/
  app/
    main.py                 # HTTP/WebSocket入口
    config.py               # 配置和安全默认值
    protocol/               # APDU/ASDU编码、TCP流解帧
    robot/                  # 状态聚合、保活、重连
    navigation/             # 门控、单点和多点状态机
    video/                  # RTSP探测和转码进程监管
    map/                    # PGM/YAML读取与坐标转换
    api/                    # read-only/control路由分离
  tests/
frontend/
  src/
    status/
    video/
    map/
    navigation/
deploy/
  systemd/
  scripts/
config/
  example/
docs/
```

## 4. 分任务实施

### Task 1：协议编解码核心

**文件：**
- 创建 `backend/app/protocol/frame.py`
- 创建 `backend/app/protocol/messages.py`
- 测试 `backend/tests/protocol/test_frame.py`

**步骤：**
1. 先写16字节头部编码失败测试：同步字、ASDU UTF-8字节长度、小端消息ID、JSON格式位。
2. 执行测试并确认因实现缺失而失败。
3. 最小实现编码器。
4. 增加TCP粘包、拆包、多帧和非法同步字测试。
5. 实现增量流解帧器并运行完整测试。
6. 提交：`feat(protocol): add basic server frame codec`。

### Task 2：状态消息解析和只读模型

**文件：**
- 创建 `backend/app/robot/models.py`
- 创建 `backend/app/robot/status_parser.py`
- 测试 `backend/tests/robot/test_status_parser.py`

**步骤：**
1. 用脱敏固定样本为`1002/3,4,5,6`和`1007/2`编写失败测试。
2. 对Sleep的bool/int版本差异做兼容测试。
3. 最小实现解析、字段缺失容错和时间戳。
4. 验证异常码保持原值且不误判未知码。
5. 提交：`feat(robot): parse M20 status reports`。

### Task 3：TCP连接、保活和重连

**文件：**
- 创建 `backend/app/robot/basic_client.py`
- 测试 `backend/tests/robot/test_basic_client.py`

**步骤：**
1. 以本地fake TCP server测试连接、1Hz心跳、主动上报、多帧和断线。
2. 测试3秒无响应进入`stale/disconnected`状态。
3. 实现带上限指数退避，不在断线重连中重复发送控制命令。
4. 验证关闭应用会取消任务并释放socket。
5. 提交：`feat(robot): add resilient basic server client`。

### Task 4：状态Web API与WebSocket

**文件：**
- 创建 `backend/app/main.py`
- 创建 `backend/app/api/status.py`
- 测试 `backend/tests/api/test_status_api.py`

**步骤：**
1. 测试`/api/v1/health`、`/api/v1/status/latest`与`/ws/status`。
2. API必须明确返回`connected/stale/simulated`来源字段。
3. 实现有界广播队列，慢客户端不能阻塞机器人连接。
4. 提交：`feat(api): stream robot status to web clients`。

### Task 5：地图与轨迹

**文件：**
- 创建 `backend/app/map/occupancy.py`
- 创建 `backend/app/api/map.py`
- 测试 `backend/tests/map/test_occupancy.py`

**步骤：**
1. 对YAML resolution/origin、PGM宽高和坐标换算写失败测试。
2. 明确像素Y翻转和边界策略；以现场地图实测确认`H`与是否减1。
3. API只读取导出的地图副本，不在Web服务中直接修改NOS地图。
4. 位姿轨迹设置采样率、最大点数和断线分段。
5. 提交：`feat(map): expose occupancy map and live track`。

### Task 6：RTSP探测与浏览器视频方案Spike

**文件：**
- 创建 `backend/app/video/probe.py`
- 创建 `docs/video-spike.md`
- 测试 `backend/tests/video/test_probe.py`

**步骤：**
1. 在GOS检查`ffmpeg/ffprobe/gstreamer`及H.265硬解能力。
2. 对两路RTSP做10分钟稳定性、码率、延迟、CPU和内存测试。
3. 比较：
   - WebRTC：低延迟首选，但实现复杂；
   - HLS：简单稳定但延迟高；
   - MSE/fMP4：中等延迟，浏览器H.265兼容性差。
4. 推荐第一版：GOS将RTSP/H.265转为WebRTC/H.264；若依赖不足，演示降级为低延迟HLS/H.264。
5. 转码必须使用进程监管、超时、重启限速和资源上限。
6. 提交：`spike(video): validate dual RTSP browser delivery`。

### Task 7：前端状态、视频和轨迹页

**文件：**
- 创建 `frontend/src/...`
- 测试 `frontend/tests/...`

**步骤：**
1. 先实现断线/模拟/真实状态明确标识。
2. 两路视频卡片分别显示连接、首帧、延迟和重连状态。
3. 地图叠加当前位姿和历史轨迹；定位丢失时轨迹停止延伸。
4. 显示电量、急停、模式、步态、姿态、CPU/温度、异常列表。
5. 提交：`feat(web): add live patrol dashboard`。

### Task 8：导航安全门控

**文件：**
- 创建 `backend/app/navigation/interlock.py`
- 测试 `backend/tests/navigation/test_interlock.py`

**步骤：**
1. 分别为每个禁止条件写失败测试。
2. 未知/缺失状态必须fail-closed。
3. 只有所有条件通过才产生“允许派发”结果；门控模块本身不发送网络报文。
4. 提交：`feat(navigation): add fail-closed safety interlock`。

### Task 9：单点导航和取消

**文件：**
- 创建 `backend/app/navigation/service.py`
- 创建 `backend/app/api/navigation.py`
- 测试 `backend/tests/navigation/test_service.py`

**步骤：**
1. 使用fake basic_server测试`1003/1`、`1004/1`和`1007/1`。
2. 测试任务响应可能直到成功/失败/取消后才返回，禁止阻塞Web事件循环。
3. 第一期只允许`PointInfo=1`、平地步态、低速、前进、停避障开启、自主导航。
4. 增加幂等、互斥、超时、取消和审计日志。
5. 提交：`feat(navigation): add guarded point navigation`。

### Task 10：多点巡逻状态机

**文件：**
- 创建 `backend/app/navigation/patrol.py`
- 测试 `backend/tests/navigation/test_patrol.py`

**步骤：**
1. 测试点位串行、到点停留、失败停止、取消和恢复需人工确认。
2. 不允许当前任务未结束时下发下一任务。
3. 每个点位记录开始、到达、错误、耗时和操作员。
4. 提交：`feat(patrol): orchestrate multi-point routes`。

### Task 11：部署与回滚

**文件：**
- 创建 `deploy/systemd/m20-patrol.service`
- 创建 `deploy/scripts/install.sh`
- 创建 `deploy/scripts/rollback.sh`
- 创建 `docs/deployment.md`

**步骤：**
1. 以非root用户运行；工作目录和配置独立。
2. 使用`taskset -c 4-7`，设置资源和重启限制。
3. 安装脚本默认`ROBOT_CONTROL_ENABLED=false`。
4. 部署前备份旧版本，按固定Git commit安装。
5. 先在本地容器/模拟器验证，再由用户在GOS执行。
6. 提交：`chore(deploy): add controlled GOS deployment`。

## 5. 验收门槛

### 离线验收

- 协议编解码、粘包拆包、状态解析、断线重连测试全部通过。
- 无真实机器人时可用记录样本重放，但UI必须显示`SIMULATED`。
- 控制开关默认关闭，API无法绕过门控。
- 两路视频源断开不会导致后端失控或资源泄漏。

### GOS只读验收

- 确认系统版本、架构、Python、磁盘、CPU、端口和工具。
- 连续30分钟接收状态，无解析崩溃；3秒断线检测正确。
- 两路RTSP连续30分钟，记录CPU、内存、带宽和端到端延迟。
- Web页面连续显示状态、地图和轨迹，不修改任何原厂服务。

### 实机导航验收（需另行现场安全批准）

- 版本和地图经确认；遥控器、软急停、硬急停均可用。
- 空旷平地，周围至少2米隔离，专人持遥控器。
- 单个低速点位；定位正常；停避障开启。
- 验证完成、取消、停障、定位丢失模拟和断链行为。
- 通过后才扩展到多点，楼梯和室外另立测试计划。

## 6. 当前阻塞项

- 现场M20 Pro系统版本未知；官方更新说明表明V1.1.7/V1.1.8包含关键安全和导航修复。
- GOS上Python、FFmpeg/GStreamer、容器和包管理能力未知。
- 当前激活地图和定位质量未知。
- 浏览器视频最终选型必须由GOS实测决定。
- 官方文档中旧PDF和在线指南的步态值存在版本差异，必须按现场版本绑定协议表，不能混用。
