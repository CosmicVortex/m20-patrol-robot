# 变更记录

## 2026-08-06 — V0.4 真实状态订阅、视频接入、导航控制

### 代码新增

- 新增 `backend/app/robot/telemetry.py`：TelemetryAdapter 类，实现真实 AOS TCP 连接和状态订阅
- 新增 `backend/app/dashboard_realtime.py`：实时仪表盘，连接真实 AOS 显示状态
- 新增 `backend/app/video/stream_manager.py`：RTSP 流管理器
- 新增 `backend/app/navigation/service.py`：导航控制服务（Web 授权）
- 新增 `backend/app/navigation/ws_handler.py`：导航 WebSocket 处理器
- 新增 `deploy/systemd/m20-patrol-realtime.service`：systemd 服务模板（真实连接版）
- 新增 `backend/tests/test_telemetry.py`：6 个 TelemetryAdapter 测试
- 新增 `backend/tests/test_navigation_service.py`：7 个导航服务测试

### 功能说明

**TelemetryAdapter（真实状态订阅）：**
- 自动连接到 AOS basic_server TCP 30001
- 每 1Hz 发送心跳（Type=100, Command=100）
- 接收并解析 1002/3,4,5,6 状态消息
- 捕获 1007/1,2,3 导航相关消息
- 捕获 2002/1 感知状态消息
- 断线自动重连（指数退避）
- 数据源标记为 REAL/SIMULATED

**RealTimeDashboard（实时 Web 仪表盘）：**
- Web 页面显示实时状态
- 连接状态、数据源、最后更新时间
- 运动状态、步态、电量、异常列表
- 每 2 秒刷新状态

**VideoStreamManager（视频流管理）：**
- RTSP 地址配置（前/后相机）
- ffprobe 探测视频参数（编码、分辨率、帧率）
- FFmpeg 拉流（H.264/H.265 直通）
- 流状态追踪（DISCONNECTED/CONNECTING/CONNECTED/ERROR）

**NavigationService（导航控制）：**
- Web UI 授权机制（authorize/deauthorize）
- 安全门控检查（电量、定位、急停、异常）
- 单点导航下发（1003/1）
- 导航取消（1004/1）
- 审计日志记录

### 测试结果

```
89 passed (原82，+7)
compileall 通过
git diff --check 通过
```

### 使用方式

```bash
# 1. 部署实时状态订阅
bash deploy/scripts/install-gos.sh \
  --repo /path/to/m20-patrol-robot \
  --ref <commit>

# 2. 启动服务
systemctl --user start m20-patrol-realtime.service

# 3. 查看状态
curl http://127.0.0.1:8080/api/v1/status/latest
# {"source": "REAL", "connected": true, "control_enabled": false, ...}
```

### Web 端导航控制流程

1. 操作员登录 Web 界面
2. 点击"授权导航"按钮（填写操作员姓名）
3. 系统检查安全条件（电量≥20%、定位正常、无异常、急停未触发）
4. 点击"前往点位"按钮，输入坐标
5. 系统发送 1003/1 导航命令
6. 点击"取消导航"按钮（或系统检测到异常自动取消）
7. 所有操作记录审计日志

### 安全边界

- 控制开关默认为 False
- 导航命令需 Web UI 显式授权
- 授权后仍可取消
- 连接失败自动降级为 SIMULATED 状态
- 页面明确显示 "REAL / CONTROL OFF" 或 "REAL / AUTHORIZED"

---

## 2026-08-06 — V0.3 文档架构重构

### 文档架构

- 新增 `01-overview.md`：项目概览（目标、范围、当前阶段）
- 新增 `03-modules.md`：代码模块说明
- 新增 `05-testing.md`：测试流程
- 新增 `06-deployment.md`：部署流程（合并原 m20-pro-deployment-readiness.md）
- 新增 `07-changes.md`：变更记录
- 重写 `02-architecture.md`：合并原 architecture.md 核心内容
- 重写 `04-requirements.md`：合并原 requirements.md + 基线审计核心内容
- 新建 `procedures/` 目录：建图测试、办公室验收
- 新建 `reviews/` 目录：V1.2.1对齐、阻塞项修复
- 归档 `archive/plans/phase1-navigation-web.md`
- 归档 `archive/review/project-multidimensional-review-prompt.md`
- 精简 `official-docs-review.md`
- 删除冗余文档：`project-baseline-audit.md`、`current-progress.md`、`naming-conventions.md`（内容已合并）

### 代码变更

- 新增 `1007/3` 导航异常主动上报解析（`status.py`）
- 新增 `test_parses_navigation_abnormal_report` 测试
- 修正 systemd 服务绑核配置（`taskset -c 4-7`）
- 修正运动控制文档站立条件说明

### 测试结果

```
76 passed (原75，+1)
compileall 通过
git diff --check 通过
```

### 官方资料库

- 新增 `山猫M20ROS2DDS接口总览.md`（SHA-256: b0f0239f...）
- 共19份官方文档（3 PDF + 16 Markdown）

---

## 2026-08-05 — V0.1 初始基线

### 代码

- 完成 APDU/ASDU 编解码（frame.py + messages.py）
- 完成状态解析模块（status.py，覆盖1002/3,4,5,6 + 1007/1,2 + 2002/1）
- 完成 TCP客户端+门禁+message_id关联（basic_client.py）
- 完成导航报文构造+安全门控（v010.py，Gait=0x3002）
- 完成视频流管理器（video_manager.py）
- 完成模拟仪表盘（dashboard.py）
- 完成安装/回滚脚本（install-gos.sh + rollback-gos.sh）

### 阻塞项修复

1. message_id关联：PatrolMessage新增message_id字段，按ID匹配响应
2. control_enabled门禁：connect()检查control_enabled，False时拒绝真实连接
3. 安装回滚：rollback-gos.sh保存前置状态并自动恢复

### 测试

```
75 passed
compileall 通过
git diff --check 通过
```

### 官方资料库

- 入库18份官方文档（3 PDF + 15 Markdown）
