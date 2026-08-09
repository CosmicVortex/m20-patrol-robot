# 04 — 需求清单

## 需求总览

| 编号 | 需求 | 状态 | 验收证据 |
|------|------|------|----------|
| R-01 | APDU 帧编解码 | ✅ | `protocol/frame.py`、`test_frame.py` |
| R-02 | PatrolMessage 信封 | ✅ | `protocol/messages.py`、`test_messages.py` |
| R-03 | 状态监控页面 | ✅ | `dashboard_realtime.py` |
| R-04 | GOS 现场核验 | 🟡 | `deploy/scripts/collect-readonly-info.sh` |
| R-05 | 安装/回滚 | ✅ | `install-gos.sh`、`rollback-gos.sh` |
| R-06 | 真实状态订阅 | ✅ | `robot/telemetry.py`、`test_telemetry.py` |
| R-07 | 视频接入 | 🟡 | `video/stream_manager.py` |
| R-08 | 单点导航 | 🟡 | `navigation/service.py` |
| R-09 | 多点巡逻 | 🔴 | 待 R-06/R-07/R-08 验收 |
| R-10 | 云台适配 | 🔴 | 待实物确认 |

## 阶段目标

**阶段1**：完成测试场地建图、状态订阅、视频回传、单点导航控制

**阶段2**：测试场地验收通过后，正式场地重新建图并单独验收

## 验收规则

### 离线验收

```bash
PYTHONPATH=. uv run --with pytest pytest -q
```

模拟页面返回 `source=SIMULATED`、`connected=false`。

真实接入返回 `source=REAL`、`connected=true`。

### 真实接入条件

1. M20 Pro 型号、固件版本已确认
2. V1.2.1 与固件差异已记录
3. basic_server 权限已批准
4. 状态数据可读且新鲜度可判定
5. 现场安全条件已确认
6. 书面放行

## 当前实现

### R-06 真实状态订阅

AOS 地址：10.21.31.103，固件 V1.1.8

订阅的消息类型：
- `1002/6` 基础状态
- `1002/4` 运控状态
- `1002/5` 设备状态
- `1002/3` 异常列表
- `1007/1` 导航状态
- `1007/2` 位置
- `1007/3` 导航异常（≥V1.1.8）

生产模式不发送心跳，`TELEMETRY_TX_ENABLED=false`。

### R-07 视频接入

RTSP 地址（候选值）：
- 前相机：`rtsp://10.21.31.103:8554/video1`
- 后相机：`rtsp://10.21.31.103:8554/video2`

需现场确认：ffprobe、编码格式、分辨率。

### R-08 单点导航

Web 授权流程：
1. 操作员点击授权
2. 系统检查安全条件
3. 输入坐标，发送导航命令
4. 审计日志记录

默认关闭，需书面放行后启用。
