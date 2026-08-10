# M20 Pro 巡逻机器人项目 — 全面审查与修复报告

**审查日期**: 2026-08-10  
**Git HEAD**: 6c2a186  
**代码规模**: 26个Python模块，约5050行  
**测试基线**: 180 passed  

---

## 一、问题清单（按优先级分类）

### P0 — 严重问题（需立即修复）

| 编号 | 问题 | 影响 | 文件 |
|------|------|------|------|
| P0-1 | systemd服务中端口配置错误 | 服务无法连接AOS | `deploy/systemd/m20-patrol-readonly.service` |
| P0-2 | stale_after_seconds=300覆盖manifest | 健康检查失效，超时判定延迟5分钟 | 同上 |

**详情：**

1. **P0-1**: systemd服务硬编码 `M20_TARGET_PORT=8888`，但manifest配置AOS端口为30001。应用实际从manifest读取端口，此环境变量未被使用，但暴露配置不一致。

2. **P0-2**: systemd服务设置 `M20_STALE_AFTER_SECONDS=300`，而manifest配置为3秒。应用读取环境变量时优先使用env，导致生产环境下超时判定变为5分钟，健康检查将长时间报告虚假"新鲜"状态。

**修改方案：**

```bash
# deploy/systemd/m20-patrol-readonly.service
# 删除错误的M20_TARGET_PORT（应用不从env读取）
# 删除或修正M20_STALE_AFTER_SECONDS（应使用manifest值3）
```

---

### P1 — 高优先级问题（需尽快修复）

| 编号 | 问题 | 影响 | 文件 |
|------|------|------|------|
| P1-1 | `loop_count`字段永远为0 | 巡检统计无效 | `telemetry.py`, `status.py` |
| P1-2 | 私有属性`_connected`被外部访问 | 封装违规 | `gimbal/handlers.py` |
| P1-3 | 部署脚本设置未使用的env变量 | 配置混乱 | `deploy-readonly.sh` |
| P1-4 | RTSP地址硬编码 | 无法适配不同现场 | `stream_manager.py`, `handlers.py` |

**P1-1 详情：**

`telemetry.py:333` 从 `snap.nav_status` 读取 `loop_count`，但：
- `nav_status` 字段由 Type=1007 Command=1 消息填充（`_parse_navigation_status`）
- `LoopCnt` 字段仅在 Type=1007 Command=3 消息中出现（`_parse_navigation_abnormal`）
- 两种消息类型写入不同的状态字段

**结果：** `laps_today` 始终返回0，巡检统计无效。

**修复方案：**

```python
# telemetry.py:333
"laps_today": snap.nav_status.get("loop_count", 0) if snap.nav_status else 0,
# 改为：
"laps_today": snap.nav_status.get("loop_count", 0) if snap.nav_status else 0,
# 同时在 _update_snapshot_inner 中处理 navigation_abnormal 消息时更新 nav_status
```

需要在 `_update_snapshot_inner` 中添加：
```python
elif kind == "navigation_abnormal":
    self._snapshot.nav_status = data.get("nav_status", {})
```

**P1-2 详情：**

`gimbal/handlers.py` 多处访问 `gimbal._connected`（私有属性），违反封装原则。应改为公开属性 `gimbal.connected` 或方法 `gimbal.is_connected()`。

**P1-3 详情：**

部署脚本设置 `M20_TARGET_HOST` 和 `M20_TARGET_PORT`，但应用代码未读取这些环境变量（从manifest读取）。应删除或更新文档说明。

**P1-4 详情：**

以下位置硬编码RTSP地址 `10.21.31.103`：
- `stream_manager.py:51-53`（默认相机配置）
- `handlers.py:467-479`（视频状态fallback）

建议：从manifest或环境变量读取RTSP基础地址。

---

### P2 — 中优先级问题（建议修复）

| 编号 | 问题 | 影响 | 文件 |
|------|------|------|------|
| P2-1 | 命名不一致：`stale_after_s` vs `stale_after_seconds` | 可读性差 | 多处 |
| P2-2 | `dashboard_realtime.py` 为废弃入口 | 维护负担 | 文件存在但不用 |
| P2-3 | 云台默认IP `192.168.1.108` 硬编码 | 可能连接错误设备 | `adapter.py:244` |
| P2-4 | 文档缺少数据字段映射说明 | 理解困难 | `docs/` |

**P2-1 详情：**

- `BasicServerConfig.stale_after_seconds` vs `ConnectionConfig.stale_after_s` vs `WebServiceConfig.stale_after_s`
- 建议统一为 `stale_after_s`（秒浮点数）

**P2-2 详情：**

`dashboard_realtime.py` 是旧版独立入口，现已由 `server.py` 替代。建议标记为废弃或移除。

**P2-3 详情：**

云台自动发现fallback到 `192.168.1.108` 是Soar Security的常见默认IP，但若现场有多个Soar设备可能误连。建议在manifest中配置 `gimbal_default_host`。

---

## 二、数据一致性检查

### 2.1 前后端字段映射

| 后端字段 | API响应字段 | 前端使用 | 状态 |
|----------|------------|----------|------|
| `nav_status.loop_count` | `inspection_stats.laps_today` | JS读取 | ⚠️ 始终为0 |
| `position.pos_x/pos_y` | `data.position.pos_x/pos_y` | JS读取 | ✅ |
| `basic.motion_state` | `data.basic.motion_state` | JS读取 | ✅ |
| `errors[*].error_code` | `data.errors[*].error_code` | JS读取 | ✅ |

### 2.2 协议解析验证

通过手动测试验证：
```python
# Type=1007 Command=1 → nav_status (无loop_count)
# Type=1007 Command=3 → navigation_abnormal (有loop_count)
```

**结论：** `nav_status` 和 `navigation_abnormal` 应合并到同一字段，或分别存储。

### 2.3 配置匹配

| 配置项 | manifest值 | systemd服务 | 应用实际使用 |
|--------|-----------|------------|-------------|
| aos_host | 10.21.31.103 | M20_TARGET_HOST=10.21.31.103 | ✅ manifest |
| aos_port | 30001 | M20_TARGET_PORT=8888 | ✅ manifest |
| stale_after | 3s | M20_STALE_AFTER_SECONDS=300 | ⚠️ env优先 |

---

## 三、代码冗余检查

### 3.1 重复定义

| 位置 | 内容 | 状态 |
|------|------|------|
| `config.py:16-52` | `WebServiceConfig` | ✅ 唯一 |
| `dashboard_realtime.py:28-56` | `DashboardConfig` | ⚠️ 冗余定义 |
| `telemetry.py:35-59` | `ConnectionConfig` | ✅ 唯一 |
| `basic_client.py:53-80` | `BasicServerConfig` | ✅ 唯一 |

### 3.2 废弃代码

`dashboard_realtime.py` 约730行，包含：
- 独立配置类（与`WebServiceConfig`重复）
- HTML渲染逻辑（已在`server.py`中移除）
- 独立的TCP连接管理

**建议：** 标记为`@deprecated`或移至`archive/`目录。

---

## 四、逻辑正确性检查

### 4.1 连接管理

**telemetry.py `_run_loop` 逻辑：**
```python
# 正确：模拟模式不创建客户端
if runtime_mode == "simulated":
    # 使用模拟数据

# 正确：先检查receive_enabled
if not telemetry_receive_enabled:
    return

# 正确：每次连接创建新客户端
client = BasicServerClient(config)
self._client = client
```

**结论：** 连接管理逻辑正确。

### 4.2 门禁检查

**basic_client.py `connect` 方法：**
```python
# read_only=True：仅需验证超时
# control_enabled=True：需要三份证据
```

**结论：** 门禁逻辑完整。

### 4.3 异常处理

**telemetry.py 异常处理：**
- `ClientStateError` → 警告+重连
- 其他异常 → 错误日志+重连
- 无异常丢失

**结论：** 异常处理健壮。

---

## 五、命名规范检查

### 5.1 PEP 8符合性

| 检查项 | 状态 |
|--------|------|
| 函数/变量名使用snake_case | ✅ |
| 类名使用PascalCase | ✅ |
| 常量使用UPPER_SNAKE_CASE | ✅ |
| 私有属性使用`_`前缀 | ✅（但`_connected`应公开） |
| 类型注解完整 | ✅ |
| docstring存在 | ✅ |

### 5.2 命名不一致

| 不一致项 | 位置 | 建议 |
|----------|------|------|
| `stale_after_s` vs `stale_after_seconds` | 多文件 | 统一为`stale_after_s` |
| `telemetry_tx_enabled` vs `transmit_enabled` | `ConnectionConfig` vs `BasicServerConfig` | 统一命名 |

---

## 六、配置管理检查

### 6.1 环境变量使用

| 环境变量 | 是否使用 | 来源 |
|----------|---------|------|
| `M20_GIMBAL_PASSWORD` | ✅ | config.py:97 |
| `M20_ADMIN_PASSWORD` | ✅ | server.py:143 |
| `M20_STALE_AFTER_SECONDS` | ✅ | config.py:90 |
| `M20_TARGET_HOST` | ❌ 未使用 | deploy-readonly.sh:170 |
| `M20_TARGET_PORT` | ❌ 未使用 | deploy-readonly.sh:171 |

### 6.2 硬编码值

| 位置 | 值 | 建议 |
|------|-----|------|
| `stream_manager.py:51-53` | RTSP地址 | 从manifest读取 |
| `adapter.py:244` | 云台默认IP | 从manifest读取 |
| `handlers.py:467-479` | RTSP fallback | 从manifest读取 |

---

## 七、测试覆盖检查

### 7.1 覆盖率统计

| 模块 | 测试文件 | 测试数 | 状态 |
|------|---------|--------|------|
| `protocol/frame.py` | `test_frame.py` | 20 | ✅ |
| `protocol/messages.py` | `test_messages.py` | 8 | ✅ |
| `robot/status.py` | `test_status.py` | 12 | ✅ |
| `robot/basic_client.py` | `test_basic_client.py` | ~15 | ✅ |
| `robot/telemetry.py` | `test_telemetry.py` | 15 | ✅ |
| `navigation/v010.py` | `test_navigation_v010.py` | ~20 | ✅ |
| `navigation/service.py` | `test_navigation_service.py` | ~10 | ✅ |
| `auth/store.py` | `test_auth_store.py` | 12 | ✅ |
| `auth/middleware.py` | `test_auth_middleware.py` | 11 | ✅ |
| `api/handlers.py` | `test_api_router.py` | 10 | ⚠️ 仅路由 |
| `gimbal/adapter.py` | `test_gimbal_adapter.py` | 13 | ✅ |
| `video/stream_manager.py` | `test_video_stream_manager.py` | 8 | ✅ |
| `config.py` | `test_config.py` | ~8 | ✅ |

**总计：180 passed**

### 7.2 缺失测试

| 模块 | 缺失测试 |
|------|---------|
| `api/handlers.py` | 登录、状态、导航等具体handler逻辑 |
| `gimbal/handlers.py` | 云台handler认证逻辑 |
| `server.py` | 集成测试 |

---

## 八、文档质量检查

### 8.1 术语专业化

| 术语 | 使用 | 建议 |
|------|------|------|
| AOS/GOS/NOS | ✅ 一致 | - |
| basic_server | ✅ 一致 | - |
| APDU/ASDU | ✅ 专业 | - |
| 遥测 | ✅ | 或"telemetry" |

### 8.2 AI痕迹检查

扫描文档关键词：
- "首先"：0处 ✅
- "其次"：0处 ✅
- "综上所述"：0处 ✅
- "值得注意的是"：0处 ✅
- "此外"：2处（可接受）

**结论：** 无明显AI生成痕迹。

### 8.3 结构合理性

文档结构：
```
docs/
├── index.md              # 导航 ✅
├── 01-overview.md        # 概览 ✅
├── 02-architecture.md    # 架构 ✅
├── 03-modules.md         # 模块 ✅
├── 04-requirements.md    # 需求 ✅
├── 05-testing.md         # 测试 ✅
├── 06-deployment.md      # 部署 ✅
└── 09-official-docs.md   # 参考 ✅
```

**结论：** 结构清晰合理。

---

## 九、修复方案

### 9.1 P0修复：修正systemd服务配置

**文件：** `deploy/systemd/m20-patrol-readonly.service`

```diff
-Environment=M20_TARGET_HOST=10.21.31.103
-Environment=M20_TARGET_PORT=8888
-Environment=M20_STALE_AFTER_SECONDS=300
+Environment=M20_STALE_AFTER_SECONDS=3
```

**验证：**
```bash
# 检查服务文件
grep -E "TARGET|STALE" deploy/systemd/m20-patrol-readonly.service
# 应输出：M20_STALE_AFTER_SECONDS=3
```

### 9.2 P1-1修复：修正loop_count数据流

**文件：** `backend/app/robot/telemetry.py`

```diff
  elif kind == "nav_status":
      self._snapshot.nav_status = data
+ elif kind == "navigation_abnormal":
+     self._snapshot.nav_status = data.get("nav_status", {})
```

**验证：**
```python
# 手动测试
from backend.app.robot.status import parse_status_message
from backend.app.protocol.messages import PatrolMessage
result = parse_status_message(PatrolMessage(1007, 3, '2026-08-06', {
    'NavStatus': {'LoopCnt': 5, 'ErrorCode': 0}
}))
# 应返回 navigation_abnormal，包含loop_count=5
```

### 9.3 P1-2修复：暴露connected属性

**文件：** `backend/app/gimbal/adapter.py`

```diff
  def close(self) -> None:
      self.stop_heartbeat()
      with self._lock:
          self._session = None
          self._connected = False
+     logger.info("云台连接已关闭")
+
+ @property
+ def connected(self) -> bool:
+     return self._connected
```

**文件：** `backend/app/gimbal/handlers.py`

```diff
-        if not gimbal or not gimbal._connected:
+        if not gimbal or not gimbal.connected:
```

### 9.4 P1-3修复：清理部署脚本

**文件：** `deploy/scripts/deploy-readonly.sh`

```diff
-Environment=M20_TARGET_HOST=${AOS_HOST}
-Environment=M20_TARGET_PORT=${AOS_TCP_PORT}
+Environment=M20_RUNTIME_MODE=realtime_readonly
```

---

## 十、验证方法

### 10.1 单元测试验证

```bash
cd /opt/data/m20-patrol-robot
PYTHONPATH=. uv run --with pytest pytest backend/tests/ -v
# 预期：180 passed
```

### 10.2 编译验证

```bash
python3 -m compileall -q backend/
# 预期：无错误
```

### 10.3 集成验证（GOS环境）

```bash
# 部署后检查
curl http://127.0.0.1:8080/api/v1/health
# 预期：source=REAL, connected=true, valid_frames>0

curl http://127.0.0.1:8080/api/v1/status/latest
# 预期：inspection_stats.laps_today有实际值
```

### 10.4 配置验证

```bash
# 检查systemd服务
grep M20_STALE systemctl show m20-patrol-readonly.service --property=Environment
# 预期：M20_STALE_AFTER_SECONDS=3
```

---

## 十一、修复文件清单

| 优先级 | 文件 | 修改内容 |
|--------|------|---------|
| P0 | `deploy/systemd/m20-patrol-readonly.service` | 修正stale_after=3，删除无效env |
| P1-1 | `backend/app/robot/telemetry.py` | 添加navigation_abnormal→nav_status映射 |
| P1-2 | `backend/app/gimbal/adapter.py` | 添加`connected`公开属性 |
| P1-2 | `backend/app/gimbal/handlers.py` | 改用公开属性 |
| P1-3 | `deploy/scripts/deploy-readonly.sh` | 删除未使用env变量 |

---

## 十二、总结

### 发现的问题统计

| 优先级 | 数量 | 类别 |
|--------|------|------|
| P0 | 2 | 配置错误 |
| P1 | 4 | 数据流、封装、配置 |
| P2 | 4 | 命名、冗余、文档 |

### 代码质量评分

| 维度 | 评分 | 说明 |
|------|------|------|
| 数据一致性 | ⚠️ 7/10 | loop_count字段映射问题 |
| 代码冗余 | ✅ 9/10 | 仅dashboard_realtime.py废弃 |
| 逻辑正确性 | ✅ 9/10 | 门禁、异常处理良好 |
| 命名规范 | ⚠️ 8/10 | 命名不一致 |
| 配置管理 | ⚠️ 7/10 | 硬编码和无效env |
| 测试覆盖 | ✅ 9/10 | 核心逻辑覆盖充分 |
| 文档质量 | ✅ 9/10 | 专业、无AI痕迹 |

### 总体评价

代码质量良好，安全门禁设计严谨，测试覆盖充分。主要问题集中在：
1. **部署配置错误**（P0）— 可能影响生产环境健康检查
2. **数据字段映射缺陷**（P1）— 巡检统计无效
3. **封装违规**（P1）— 私有属性访问

建议优先修复P0和P1-1，其余按P1-2/P1-3/P2顺序处理。

---

**审查完成时间**: 2026-08-10 18:30 UTC  
**审查者**: Hermes Agent  
**下一步**: 执行修复并重新运行测试验证
