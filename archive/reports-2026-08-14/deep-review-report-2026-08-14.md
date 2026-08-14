# M20 Pro 深度审查报告 - 2026-08-14

**审查范围**: 代码实现 vs 需求文档 vs 官方协议文档  
**审查结论**: 核心功能完整，存在若干一致性问题和待修复项

---

## 一、需求完成度分析

### 1.1 已实现功能（对照需求文档）

| 功能模块 | 需求描述 | 实现状态 | 代码路径 | 置信度 |
|----------|----------|----------|----------|--------|
| 状态监控 | 机器狗位置、电量、运动状态实时刷新 | ✅ 完整 | `robot/telemetry.py`, `robot/status.py` | 高 |
| 视频回传 | 前/后广角+热成像+云台可见光四路视频 | ⚠️ 框架完成 | `video/stream_manager.py` | 中 |
| 运动控制 | 前进/后退/左转/右转/急停/回充 | ✅ 完整 | `motion/service.py`, `motion/handlers.py` | 高 |
| 导航控制 | 单点导航、任务管理 | ✅ 完整(M20 Pro) | `navigation/service.py`, `navigation/protocol.py` | 高 |
| 云台控制 | 方向调节、变倍、激光测距 | ✅ 完整 | `gimbal/adapter.py` | 高 |
| 异常告警 | 错误码解析、告警工单管理 | ✅ 完整 | `api/extended_handlers.py`(work-orders) | 高 |
| 认证鉴权 | 用户登录、会话管理 | ✅ 完整 | `auth/middleware.py`, `auth/store.py` | 高 |
| 巡检管理 | 巡检点配置、覆盖率统计 | ⚠️ 基础实现 | `api/extended_handlers.py`(inspection-points) | 中 |
| AI识别 | 人/车区分识别 | ❌ 未实现 | - | - |
| 异常告警规则 | 火情/陌生人自动检测 | ❌ 未实现 | - | - |

### 1.2 功能缺口分析

**已确认未实现（低优先级）**：
- AI识别接入（Type=2002/1仅获取感知状态，无AI推理）
- 异常告警自动触发规则（当前仅被动接收错误码）

**框架已实现但需配置**：
- 视频流管理（RTSP地址需从manifest读取，当前硬编码）
- 巡检覆盖率统计（仅存储点位，无覆盖率计算逻辑）

---

## 二、代码与文档一致性审查

### 2.1 模块说明文档 vs 实际代码

| 文档描述 | 实际代码 | 一致性 | 问题 |
|----------|----------|--------|------|
| `protocol/frame.py` APDUHeader类 | 实际使用FrameLayout+FrameCodec | ⚠️ 不一致 | 文档描述的类结构已重构，但未更新文档 |
| `BasicServerConfig` tcp_port=30001 | 实际默认值30001 | ✅ 一致 | - |
| `StatusSnapshot` device字段 | 实际包含battery_list等 | ⚠️ 不完整 | 文档未列出所有子字段 |
| API路径 `/api/v1/gimbal/angle` | 实际未实现此端点 | ❌ 文档错误 | 模块说明列出的路径不存在 |

### 2.2 部署说明 vs 实际脚本

| 文档描述 | 实际实现 | 一致性 | 问题 |
|----------|----------|--------|------|
| `build-offline-deploy-package.sh` | 脚本存在 | ✅ | - |
| `install-ffmpeg-offline.sh` | 脚本存在 | ✅ | - |
| `systemctl status m20-patrol-readonly` | 实际服务名含`-readonly`后缀 | ✅ | - |
| 密码文件路径 `~/.config/m20-patrol/passwords.env` | 实际路径正确 | ✅ | - |

### 2.3 官方协议文档 vs 代码实现

**APDU头部结构** (V1.2.1 §1.1.5):
```
文档: [0xeb, 0x91, 0xeb, 0x90, len(2), msg_id(2), format(1), reserved(7)]
代码: FrameLayout(sync_word=b'\xeb\x91\xeb\x90', length_offset=4, ...)
一致性: ✅ 匹配
```

**心跳机制** (V1.2.1 §1.2.1):
```
文档: Type=100, Command=100, ≥1Hz
代码: _HEARTBEAT=(100, 100), heartbeat_interval_s=1.0
一致性: ✅ 匹配
```

**导航参数默认值** (V1.2.1 §3.1):
```
文档: Value=0, MapID=0, Speed=0(NORMAL)
代码: value=0, map_id=0, Speed=SPEED_NORMAL(0)
一致性: ✅ 已对齐(历史修复)
```

---

## 三、安全问题审查

### 3.1 已修复问题

| ID | 问题 | 状态 |
|----|------|------|
| SEC-01 | 明文密码硬编码 | ✅ 已清理(仅保留演示默认) |
| SEC-02 | 紧急停止绕过安全门控 | ⚠️ 部分修复(见下方) |
| SEC-03 | admin权限检查注释 | ⚠️ 测试模式残留 |

### 3.2 待修复安全问题

**SEC-04: EmergencyStopHandler直接调用_client**
- 位置: `handlers.py:447-455`
- 问题: 绕过MotionControlService安全检查，直接发送软急停
- 风险: 可能绕过电量/故障检查
- 建议: 通过`motion_service.motion_state_switch(MOTION_STATE_SOFT_ESTOP)`调用

**SEC-05: 运动控制handler权限检查被注释**
- 位置: `motion/handlers.py:37,73,109...`
- 问题: `if auth.role != "admin":` 被注释，测试模式允许非admin操作
- 风险: 演示模式安全降级
- 建议: 添加配置开关区分测试/生产模式

**SEC-06: 默认密码123456**
- 位置: `server.py:191`
- 问题: 首次启动自动创建admin/123456账户
- 风险: 未修改密码即暴露
- 建议: 添加"首次启动强制修改密码"提示

---

## 四、代码质量问题

### 4.1 硬编码问题

| 位置 | 硬编码内容 | 建议方案 |
|------|-----------|----------|
| `stream_manager.py:53-54` | RTSP地址硬编码 | 从manifest.targets读取 |
| `handlers.py:505,512` | 视频URL默认值 | 从config读取 |
| `gimbal/adapter.py:246` | 默认云台IP | 从manifest.targets.gimbal_host读取 |

### 4.2 数据映射问题

**device状态字段未完全解析**:
```python
# status.py _normalize_device() 仅提取部分字段
# 缺失: CPU温度、GPS坐标、LED状态等
```

**battery_percent计算**:
```python
# telemetry.py:447-463
# 当前逻辑: 优先使用battery_list[0].BatteryLevel
# 问题: 未处理双电池取平均或最低值场景
```

### 4.3 命名不一致

| 文档命名 | 代码命名 | 差异 |
|----------|----------|------|
| `BasicServerClient` | 一致 | - |
| `TelemetryAdapter` | 一致 | - |
| `VideoStreamManager` | 一致 | - |
| `SoarGimbalAdapter` | 一致 | - |
| `NavigationService` | 一致 | - |

---

## 五、部署可行性评估

### 5.1 云端验证结果

| 检查项 | 结果 | 命令 |
|--------|------|------|
| Python编译 | ✅ 通过 | `python3 -m compileall backend/` |
| 单元测试 | ✅ 232通过 | `pytest backend/tests/ -q` |
| f-string日志 | ✅ 无违规 | grep检查结果 |
| alert()/confirm()残留 | ✅ 已替换为Toast | grep检查结果 |
| 硬编码IP检查 | ⚠️ 4处 | 见上方表格 |

### 5.2 GOS现场验证要求

**必须验证**：
```bash
# 1. FFmpeg RTSP支持
ffmpeg -hide_banner -demuxers 2>/dev/null | grep -q rtsp && echo "OK"

# 2. TCP连接AOS
nc -zv 10.21.31.103 30001

# 3. 健康检查
curl -s http://10.21.31.104:8080/api/v1/health | jq .

# 4. 遥测数据源
curl -s http://10.21.31.104:8080/api/v1/status/latest | jq '.source'
```

**预期结果**：
- source字段应为`REAL`或`SIMULATED`
- connected字段应为`true`
- telemetry_fresh应为`true`

---

## 六、文档整理建议

### 6.1 需更新的文档

| 文档 | 问题 | 更新内容 |
|------|------|----------|
| 03-模块说明.md | APDUHeader类描述过时 | 更新为FrameLayout/FrameCodec说明 |
| 03-模块说明.md | gimbal/angle端点不存在 | 删除该API条目 |
| 04-机器狗环境说明.md | systemctl命令缺少--user | 统一添加--user参数 |
| 05-部署说明.md | manifest示例字段不一致 | 对齐实际readonly-manifest.json |

### 6.2 需新增的文档

| 文档 | 内容 | 优先级 |
|------|------|--------|
| 现场配置指南.md | RTSP地址配置、云台密码修改流程 | 高 |
| 故障排查手册.md | 常见问题及解决方案 | 中 |

---

## 七、改进清单

### 7.1 高优先级（影响功能）

| ID | 问题 | 修复方案 |
|----|------|----------|
| P1-1 | RTSP地址硬编码 | 从manifest.targets读取 |
| P1-2 | EmergencyStopHandler绕过安全门控 | 改用motion_service调用 |
| P1-3 | device字段解析不完整 | 补充CPU/GPS/LED字段 |

### 7.2 中优先级（代码质量）

| ID | 问题 | 修复方案 |
|----|------|----------|
| P2-1 | 运动控制admin检查注释 | 添加MODE_TEST开关 |
| P2-2 | 默认密码123456无提示 | 启动时打印修改提示 |
| P2-3 | 模块说明文档过时 | 同步代码实际结构 |

### 7.3 低优先级（体验优化）

| ID | 问题 | 修复方案 |
|----|------|----------|
| P3-1 | 视频流未配置时前端无提示 | 添加"配置中"状态显示 |
| P3-2 | 巡检覆盖率统计缺失 | 添加覆盖率计算逻辑 |

---

## 八、最终结论

**项目状态**: 可部署（代码层面）

| 维度 | 评分 | 说明 |
|------|------|------|
| 功能完整度 | 85% | 核心功能完整，AI识别未实现(低优先级) |
| 协议对齐度 | 95% | 与V1.2.1高度对齐，少量字段待完善 |
| 代码质量 | 80% | 无严重Bug，存在硬编码和权限注释问题 |
| 文档一致性 | 75% | 模块说明部分过时，需同步更新 |
| 部署就绪度 | 90% | 脚本就绪，待现场FFmpeg和连接验证 |

**建议行动**:
1. 执行P1-1/P1-2修复（硬编码、安全门控）
2. 更新03-模块说明.md文档
3. GOS现场验证FFmpeg和TCP连接
4. 部署后修改默认密码

---

**审查完成时间**: 2026-08-14  
**下次审查触发**: 代码修改后或现场验证完成后
