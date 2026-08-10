# M20 Pro 巡检监控中心 v2 部署说明

## 变更概述

全新仪表盘界面，完全复制参考截图布局，中央区域替换为4路视频流网格，所有数据来自真实M20 Pro API。

## 文件变更

```
backend/app/api/handlers.py    - 新增 EmergencyStopHandler, VideoStatusHandler
backend/app/api/router.py      - 注册新路由
backend/app/robot/telemetry.py - 修复覆盖率计算bug
docs/website/index.html        - 全新仪表板页面（548行）
```

## 新增API端点

### GET /api/v1/video
返回4路摄像头状态：
- front: 可见光主码流
- thermal: 热成像
- front_body: 机身前视角
- rear_body: 机身后视角

默认状态：BLOCKED（视频I/O默认禁用）

### POST /api/v1/emergency/stop
急停按钮接口：
- 需要admin角色认证
- 检查导航授权状态
- read-only模式下阻塞实际命令

## 仪表板功能

### 顶部统计卡片
- 在线机器狗数 ← `connected` 字段
- 今日巡检圈数 ← `nav_status.loop_count`
- 覆盖率 ← `inspection_stats.coverage_rate`
- 待处理工单 ← `errors` 数组长度

### 中央4路视频流
- 2x2网格布局
- 每路显示：摄像头名称、状态、说明
- 状态：BLOCKED（默认）/ UNVERIFIED / ONLINE
- 全屏/截图按钮（禁用状态）

### 右侧状态面板
- 机器狗图片 + #02编号
- 在线状态 + 电量百分比（来自 `device.BatteryStatus.Left.BatteryLevel`）
- 当前位置（来自 `position.pos_x/pos_y/location`）
- 最新巡检项（从errors中查找温度异常）
- 下一巡检点（来自nav_status）

### 底部时间线
- 圈次进度可视化
- 已完成圈数（绿色勾）
- 当前圈（蓝色圆点，脉冲动画）
- 已巡检距离/异常数/已派单数

### 一键应急巡检
- 右下角固定按钮
- 未授权时灰色禁用状态
- 已授权 + control_enabled=true 时可启用

## 实时更新

- 状态API：每2秒轮询
- 视频状态：每5秒轮询
- 导航状态：每10秒轮询
- 时钟：每秒更新

## 部署步骤

### 1. 确认配置
```bash
cd /opt/data/m20-patrol-robot
cat deploy/readonly-manifest.json
```

确保：
- `runtime_mode`: `realtime_readonly`
- `read_only_mode`: true
- `control_enabled`: false
- `aos_host`: `10.21.31.103`（AOS地址）

### 2. 运行测试
```bash
PYTHONPATH=. uv run --with pytest pytest -q
```

预期输出：`180 passed`

### 3. 启动服务
```bash
# 方式1：直接运行
PYTHONPATH=. uv run python -m backend.app.server --manifest deploy/readonly-manifest.json

# 方式2：使用systemd（生产环境）
sudo systemctl restart m20-patrol-realtime
```

### 4. 访问仪表板
浏览器打开：`http://10.21.31.104:8080/`

## 数据源说明

| 显示项 | API端点 | 数据字段 |
|--------|---------|----------|
| 连接状态 | /api/v1/status/latest | source, connected |
| 机器人数量 | /api/v1/status/latest | connected |
| 巡检圈数 | /api/v1/status/latest | data.nav_status.loop_count |
| 覆盖率 | /api/v1/status/latest | inspection_stats.coverage_rate |
| 电量 | /api/v1/status/latest | data.device.BatteryStatus.Left.BatteryLevel |
| 运动状态 | /api/v1/status/latest | data.basic.motion_state |
| 位置 | /api/v1/status/latest | data.position.pos_x, pos_y, location |
| 告警数 | /api/v1/status/latest | data.errors.length |
| 视频状态 | /api/v1/video | sources.*.state |
| 授权状态 | /api/v1/navigation/status | authorized, control_enabled |

## 视频流启用（可选）

如需启用真实视频流，需：

1. 确认RTSP地址（从现场ffprobe获取）
2. 修改 manifest.json：
```json
{
  "video_enabled": true,
  "rtsp_urls": {
    "front": "rtsp://10.21.31.103:8554/video1",
    "rear": "rtsp://10.21.31.103:8554/video2"
  }
}
```
3. 重启服务

## 安全约束

- ✅ 控制命令需要admin角色认证
- ✅ 导航授权需要现场手动确认
- ✅ read-only模式下阻塞实际命令
- ✅ 视频流默认禁用
- ✅ 所有状态真实显示，不伪造在线

## 待现场验收

- [ ] RTSP地址确认
- [ ] 热成像设备确认
- [ ] 地图图片导入
- [ ] 电子地图坐标标定

---
版本：v2.0.0
日期：2026-08-10
测试：180 passed
