# RTSP视频流配置修复 - 2026-08-14

## 修改内容

### 1. 代码修改

**stream_manager.py**:
- 默认allow_real_io改为True（测试阶段）
- thermal和body_front相机RTSP地址硬编码：
  - thermal: rtsp://10.21.31.103:8554/thermal
  - body_front: rtsp://10.21.31.103:8554/body_front

### 2. 配置文件修改

**readonly-manifest.json**:
- allow_real_io: false → true

### 3. 测试更新

**test_video_stream_manager.py**:
- 显式传入allow_real_io=False参数

**test_video_stream_config.py**:
- 更新thermal相机RTSP预期值

## 验证结果

```bash
pytest backend/tests/ -q
# 232 passed in 21.33s ✅
```

## 设计说明

测试阶段RTSP地址硬编码，Web可随时控制播放：
- 前端点击"播放"按钮调用POST /api/v1/video/start
- 后端启动FFmpeg进程，通过WebSocket推送H.264流
- 点击"停止"调用POST /api/v1/video/stop

## Web控制流程

```javascript
// 前端调用示例
await api.startVideo('front');  // 启动前向相机
await api.stopVideo('front');   // 停止前向相机
```

---
修复时间: 2026-08-14
