# M20 Pro 只读实时观测项目 — 全面审查报告

**审查日期**: 2026-08-09  
**审查范围**: 代码对齐、文档一致性、部署就绪性  
**当前分支**: `feat/m20-readonly-one-shot-20260808` (已同步到 origin)  
**当前提交**: `8e976d0`

---

## 执行摘要

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 离线测试 | ✅ 通过 | 114 passed (Python 3.13 & 3.8.10) |
| 编译检查 | ✅ 通过 | compileall 无错误 |
| Git 工作树 | ✅ 干净 | 无未提交变更 |
| 废弃地址 | ✅ 无 | 未发现 10.21.31.101 引用 |
| 硬编码路径 | ✅ 无 | 所有路径来自 manifest 或环境变量 |
| 协议对齐 | ✅ 已对齐 | V1.2.1 核对清单已验证 |
| 安全边界 | ✅ 已实现 | control_enabled=false, telemetry_tx_enabled=false |
| GOS 真机部署 | ❌ 阻塞 | 待用户现场执行 |
| 真实遥测验证 | ❌ 阻塞 | 待 AOS 连接确认 |

**最终结论**: `CLOUD_ENV_READY_GOS_EXECUTION_REQUIRED`

---

## 一、协议对齐检查

### 1.1 APDU 帧头 (§1.1.5)

| 字段 | 偏移 | 大小 | 字节序 | V1.2.1 定义 | 代码实现 | 状态 |
|------|------|------|--------|-------------|----------|------|
| 同步字 | 0 | 4 | - | `EB 91 EB 90` | `b"\xeb\x91\xeb\x90"` | ✅ |
| 长度 | 4 | 2 | 小端 | 2字节 | `length_offset=4, length_size=2` | ✅ |
| 报文ID | 6 | 2 | 小端 | 2字节 | `message_id_offset=6, message_id_size=2` | ✅ |
| ASDU格式位 | 8 | 1 | - | 0=XML, 1=JSON | `flags_offset=8, allowed_flags=(0,1)` | ✅ |
| 预留 | 9 | 7 | - | 0x00 | `reserved_offset=9, reserved_size=7` | ✅ |
| **头部总长** | - | **16** | - | 16字节 | `header_size=16` | ✅ |

**测试覆盖**: `test_m20_v010_layout_matches_handbook_header` 验证完整帧结构。

### 1.2 状态消息解析 (§1.3)

| Type | Command | 名称 | 频率 | 代码位置 | 状态 |
|------|---------|------|------|----------|------|
| 1002 | 6 | BasicStatus | 2Hz | `status.py:118` | ✅ |
| 1002 | 4 | MotionStatus | 10Hz | `status.py:120` | ✅ |
| 1002 | 5 | DeviceStatus | 2Hz | `status.py:122` | ✅ |
| 1002 | 3 | ErrorList | 事件驱动 | `status.py:124` | ✅ |
| 1007 | 2 | 位置查询响应 | - | `status.py:101` | ✅ |
| 1007 | 1 | 导航状态查询响应 | - | `status.py:105` | ✅ |
| 1007 | 3 | 导航异常上报 | 1Hz(≥V1.1.8) | `status.py:107` | ✅ |
| 2002 | 1 | 导航感知状态 | - | `status.py:103` | ✅ |
| 1003 | 1 | 导航任务响应 | - | `status.py:97` | ✅ |
| 1004 | 1 | 取消导航响应 | - | `status.py:99` | ✅ |

### 1.3 导航消息 (§1.4)

| Type | Command | 名称 | 代码位置 | 状态 |
|------|---------|------|----------|------|
| 1003 | 1 | 导航下发 | `v010.py:114` | ✅ |
| 1004 | 1 | 取消导航 | `v010.py:137` | ✅ |
| 1007 | 1 | 导航状态查询 | `v010.py:143` | ✅ |

### 1.4 导航错误码映射

**已实现**: 26个错误码 (0xA301~0xA40F) 完整映射在 `status.py:47-86`

### 1.5 步态常量 (V1.2.1 格式)

| 常量 | 值 | 说明 | 状态 |
|------|-----|------|------|
| GAIT_FLAT敏捷 | 0x3002 | 平地敏捷 | ✅ |
| GAIT_STAIRS敏捷 | 0x3003 | 楼梯敏捷 | ✅ |
| GAIT_FLAT标准 | 0x1001 | 基础标准 | ✅ |
| GAIT_PLATFORM标准 | 0x1002 | 高台标准 | ✅ |

**差异修复**: V0.1.0 使用十进制 (12, 13)，V1.2.1 使用十六进制 (0x3002, 0x3003) — **已修正** ✅

---

## 二、安全边界检查

### 2.1 只读模式强制

```python
# telemetry.py:39-42
read_only: bool = True  # Always True - no control commands
telemetry_receive_enabled: bool = True
telemetry_tx_enabled: bool = False  # 默认禁用
```

**验证**:
- `ConnectionConfig.__post_init__` 强制 `telemetry_tx_enabled=False` (line 53-54)
- `BasicServerConfig.control_enabled=False` 默认值 (line 55)
- `DashboardConfig` 强制 `read_only_mode=True` 且 `control_enabled=False` (line 52-53)

### 2.2 门禁系统

| 门禁 | 条件 | 代码位置 | 状态 |
|------|------|----------|------|
| control_enabled | 连接真机需显式启用 | `basic_client.py:147-148` | ✅ |
| read_only 模式 | 允许状态订阅但不发送控制 | `basic_client.py:139-145` | ✅ |
| evidence 验证 | 真机连接需协议/固件/权限证据 | `basic_client.py:149-164` | ✅ |
| message_id 关联 | 请求/响应按 ID 匹配 | `basic_client.py:193` | ✅ |

### 2.3 导航安全门控

`NavigationSafetySnapshot.validate_for_navigation()` 检查:
- control_enabled=True ✅
- field_authorization 非空 ✅
- tcp_connected=True ✅
- location_normal=True ✅
- obstacle_avoidance_active=True ✅
- hard_estop_active=False ✅
- protective_fault_active=False ✅
- battery_percent≥20 ✅
- active_task=False ✅

### 2.4 部署安全

- **无硬编码路径**: 所有路径来自 manifest 或 `$HOME`
- **无废弃地址**: 未发现 `10.21.31.101` 引用
- **manifest 单源**: `deploy/readonly-manifest.json` 是唯一配置来源
- **回滚机制**: `rollback-gos.sh` 支持完整 commit SHA 回滚
- **健康检查**: 严格验证 `source=REAL`, `telemetry_fresh=True`

---

## 三、Python 3.8.10 兼容性

### 3.1 UTC 兼容处理

```python
# 所有文件统一模式
try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc
```

**检查范围**: frame.py, messages.py, basic_client.py, status.py, telemetry.py, v010.py, service.py, dashboard_realtime.py ✅

### 3.2 类型注解

- 使用 `from __future__ import annotations` 延迟求值 ✅
- 未使用 Python 3.10+ 语法 (如 `X | Y` 联合类型) ✅

### 3.3 测试验证

```
Python 3.13: 114 passed in 1.33s
Python 3.8.10: 114 passed (隔离环境)
compileall: 通过
```

---

## 四、文档对齐检查

### 4.1 文档结构

| 文档 | 状态 | 说明 |
|------|------|------|
| `docs/01-overview.md` | ✅ 当前基线 | 项目目标、范围、阶段 |
| `docs/02-architecture.md` | ✅ 当前基线 | 系统架构、数据边界 |
| `docs/03-modules.md` | ✅ 当前基线 | 模块说明、测试对应 |
| `docs/04-requirements.md` | ✅ 当前基线 | 需求清单、验收标准 |
| `docs/05-testing.md` | ✅ 当前基线 | 测试流程、禁止项 |
| `docs/06-deployment.md` | ✅ 当前基线 | 部署流程、健康判定 |
| `docs/07-changes.md` | ✅ 当前基线 | 变更记录 |
| `docs/official-docs-review.md` | ✅ 当前基线 | 官方资料台账 |
| `docs/reviews/v121-alignment.md` | ✅ 审查记录 | V1.2.1 对齐审查 |
| `docs/reviews/blockers-fixed.md` | ✅ 审查记录 | 阻塞项修复报告 |

### 4.2 需求追踪

| 需求 | 状态 | 验收证据 |
|------|------|----------|
| R-01 APDU 帧编解码 | ✅ 已实现 | `protocol/frame.py`, `test_frame.py` |
| R-02 PatrolDevice 信封 | ✅ 已实现 | `protocol/messages.py`, `test_messages.py` |
| R-03 模拟仪表盘 | ✅ 已实现 | `dashboard.py`, `test_dashboard.py` |
| R-04 GOS 现场核验 | 🟡 脚本已实现 | `deploy/scripts/collect-readonly-info.sh` |
| R-05 安装/回滚 | ✅ 已实现 | `install-gos.sh`, `rollback-gos.sh` |
| R-06 真实状态连接 | ✅ 已实现 | `robot/telemetry.py`, `test_telemetry.py` |
| R-07 视频接入 | 🟡 基础框架 | `video/stream_manager.py` |
| R-08 单点导航 | 🟡 已实现 Web 授权 | `navigation/service.py` |
| R-09 多点巡逻 | 🔴 未实现 | 需 R-06/R-07/R-08 验收后 |
| R-10 云台/照片 | 🔴 未实现 | 需 SR-UPA810T609 实物确认 |

### 4.3 官方文档入库

**共 19 份** (3 PDF + 16 Markdown):
- V1.2.1 软件开发指南 ✅
- V0.1.0 开发手册 ✅
- 网络配置、架构说明、协议总览 ✅
- 导航任务下发、错误码、运动控制 ✅

---

## 五、测试覆盖检查

### 5.1 测试文件清单

| 测试文件 | 行数 | 覆盖模块 |
|----------|------|----------|
| `test_frame.py` | 226 | APDU 帧编解码 |
| `test_messages.py` | 76 | PatrolDevice 信封 |
| `test_basic_client.py` | 146 | TCP 客户端 + 门禁 |
| `test_status.py` | 287 | 状态消息解析 |
| `test_telemetry.py` | 152 | 真实状态订阅 |
| `test_navigation_v010.py` | 80 | 导航报文构造 |
| `test_navigation_service.py` | 170 | 导航控制服务 |
| `test_dashboard.py` | 69 | 仪表盘 |
| `test_video_stream_manager.py` | 146 | 视频流管理 |
| `test_site_assets.py` | 120 | 静态资源 |
| `test_basic_tcp_transport.py` | 82 | TCP 传输 |
| `test_navigation_commands_v010.py` | 25 | 导航命令 |

**总计**: 114 个测试用例全部通过 ✅

### 5.2 测试覆盖度评估

| 模块 | 测试覆盖 | 评估 |
|------|----------|------|
| protocol/frame.py | ✅ 完整 | 编码/解码/粘包/拆包/边界 |
| protocol/messages.py | ✅ 完整 | JSON/XML 信封验证 |
| robot/basic_client.py | ✅ 完整 | 门禁/连接/心跳/过期 |
| robot/status.py | ✅ 完整 | 所有消息类型解析 |
| robot/telemetry.py | ✅ 充分 | 状态/连接/重连逻辑 |
| navigation/v010.py | ✅ 完整 | 安全门控/参数验证 |
| navigation/service.py | ✅ 充分 | 授权/日志/错误处理 |
| dashboard_realtime.py | 🟡 部分 | 集成测试需实机 |
| video/ | 🟡 基础 | 框架已实现，待实测 |

---

## 六、部署脚本检查

### 6.1 脚本结构

| 脚本 | 功能 | 状态 |
|------|------|------|
| `deploy-readonly.sh` | 一键部署入口 | ✅ 完整 |
| `install-gos.sh` | GOS 安装/验证 | ✅ 完整 |
| `rollback-gos.sh` | 回滚到指定 commit | ✅ 完整 |
| `start.sh` | 快速启动 | ✅ 完整 |
| `collect-readonly-info.sh` | 现场取证 | 🟡 待现场使用 |

### 6.2 Preflight 检查项

```bash
✅ GOS 主机身份验证 (10.21.31.104)
✅ Python 3.8.10 运行时验证
✅ systemd 用户管理器可用
✅ 非 root 用户执行
✅ 废弃地址检查 (10.21.31.101)
✅ 冲突服务检查 (m20-patrol-realtime)
✅ manifest 完整性验证
✅ systemd unit 模板验证
✅ 工作树干净检查
```

### 6.3 Dry-run 验证

```
NO_FILES_WRITTEN=true
NO_SYSTEMD_CHANGE=true
NO_NETWORK_SIDE_EFFECT=true
```
✅ 通过

---

## 七、阻塞项与风险

### 7.1 当前阻塞项

| 阻塞项 | 状态 | 所需证据 |
|--------|------|----------|
| GOS Python 3.8.10 确认 | ❌ 待验证 | `python3.8 -c 'import sys; print(sys.version)'` |
| AOS TCP 连接 | ❌ 待验证 | `ss -ltnp | grep 30001` 或真实报文 |
| 真实遥测数据 | ❌ 待验证 | `source=REAL`, `telemetry_fresh=True` |
| RTSP endpoint 确认 | ❌ 待验证 | `ffprobe rtsp://10.21.31.103:8554/video1` |
| basic_server 第三方连接权限 | ❌ 待确认 | 现场负责人确认 |
| 1007/3 固件版本 | ❌ 待确认 | 固件 ≥V1.1.8 确认 |

### 7.2 未实现功能

| 功能 | 需求编号 | 状态 | 前置条件 |
|------|----------|------|----------|
| 多点巡逻状态机 | R-09 | 🔴 未实现 | R-06/R-07/R-08 验收通过 |
| 云台适配 | R-10 | 🔴 未实现 | SR-UPA810T609 实物确认 |
| 视频转码代理 | - | 🔴 未实现 | GOS FFmpeg 实测 |
| 地图副本服务 | - | 🔴 未实现 | NOS 访问确认 |

### 7.3 风险等级

| 风险 | 等级 | 说明 |
|------|------|------|
| 固件版本不匹配 | 🟡 中 | 1007/3 需 ≥V1.1.8，需现场确认 |
| basic_server 权限 | 🟡 中 | 需现场负责人书面确认 |
| RTSP 编码格式 | 🟡 中 | H.264/H.265 需 ffprobe 实测 |
| 办公室建图 | 🔴 高 | 建图未完成前导航禁止 |

---

## 八、审查结论

### 8.1 代码质量评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 协议对齐 | ⭐⭐⭐⭐⭐ | V1.2.1 完全对齐，差异已修复 |
| 安全边界 | ⭐⭐⭐⭐⭐ | 门禁系统完整，fail-closed 设计 |
| 测试覆盖 | ⭐⭐⭐⭐☆ | 核心模块完整，集成测试待实机 |
| 文档一致性 | ⭐⭐⭐⭐⭐ | 文档与代码同步更新 |
| 部署就绪 | ⭐⭐⭐☆☆ | 脚本完整，待 GOS 现场执行 |
| Python 3.8 兼容 | ⭐⭐⭐⭐⭐ | 双环境测试通过 |

### 8.2 部署就绪性

**云端环境**: ✅ 就绪  
- 代码完整、测试通过、文档齐全
- 部署脚本经过 dry-run 验证
- 无硬编码、无废弃地址、无安全漏洞

**GOS 环境**: ❌ 待执行  
- 需要用户在 GOS 本机执行 `deploy-readonly.sh --one-shot`
- 需要真实遥测数据确认才能判定 `REAL`

### 8.3 最终结论

```
状态: CLOUD_ENV_READY_GOS_EXECUTION_REQUIRED

可部署性: 代码和脚本已就绪，但不得声称已部署或通信完成
下一步: 用户在 GOS 执行部署脚本并返回真实遥测证据
```

---

## 九、建议改进项

| 优先级 | 项目 | 建议 |
|--------|------|------|
| 🟡 中 | 视频接入 | GOS 实测 RTSP endpoint，确认编码格式 |
| 🟡 中 | 固件版本 | 确认 AOS 固件 ≥V1.1.8 以支持 1007/3 |
| 🟢 低 | 日志记录 | 考虑添加结构化日志 (当前仅 print) |
| 🟢 低 | 监控告警 | 添加服务健康监控和告警机制 |

---

**审查完成时间**: 2026-08-09  
**审查者**: 技术主开发智能体  
**下次审查**: GOS 部署完成后进行真机验证审查
