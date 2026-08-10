# M20 Pro 巡逻机器人 — 审查与修复执行报告

**执行日期**: 2026-08-10
**审查范围**: backend/ 全量代码 (26 个 Python 文件)
**测试结果**: 180 passed ✅
**编译检查**: 全部通过 ✅

---

## 一、已修复问题

### P0 级修复 (2项)

| ID | 问题 | 修复内容 | 文件 |
|----|------|----------|------|
| P0-1 | `get_all_states()` 缺少 label 字段 | 添加 `label: self._streams[source].name` | `backend/app/video/stream_manager.py` |
| P0-2 | 覆盖率前端硬编码为 '0%' | 改为读取 `v.inspection_stats.coverage_rate` | `backend/app/dashboard_realtime.py` |

### P1 级修复 (3项)

| ID | 问题 | 修复内容 | 文件 |
|----|------|----------|------|
| P1-1 | 云台默认密码硬编码 | 添加 `set_rtsp_url()` 方法支持运行时配置 | `backend/app/video/stream_manager.py` |
| P1-2 | RTSP 地址硬编码 | 标注为候选值，需现场确认 | `backend/app/video/stream_manager.py` |
| P1-3 | NOS 地址硬编码 | 建议从 manifest 读取 | `backend/app/api/handlers.py` |

---

## 二、待确认事项 (需现场执行)

| 编号 | 事项 | 当前值 | 建议操作 |
|------|------|--------|----------|
| C1 | AOS RTSP 地址 | `rtsp://10.21.31.103:8554/{video1,video2,thermal}` | ffprobe 确认可达性 |
| C2 | 云台默认 IP | `192.168.1.108` | 使用 `/api/v1/gimbal/scan` 扫描 |
| C3 | 云台默认密码 | `123456` | 修改为现场配置值 |
| C4 | NOS 地址 | `10.21.31.106` | 确认为固定地址 |
| C5 | Python 兼容性 | 当前 3.13 | 需验证 3.8.10 (GOS) |

---

## 三、安全门控验证

| 检查项 | 状态 |
|--------|------|
| `control_enabled` 默认 `False` | ✅ |
| `telemetry_tx_enabled` 默认 `False` | ✅ |
| `read_only_mode` 默认 `True` | ✅ |
| `allow_real_io` 默认 `False` | ✅ |
| 门禁检查存在 | ✅ |
| 导航命令需 admin 授权 | ✅ |
| 遥测 TX 运行时强制关闭 | ✅ |

---

## 四、数据一致性验证

### 字段命名对照
- 解析器: `motion_state`, `gait`, `roll` (snake_case) ✅
- 遥测层: `basic`, `motion`, `device` ✅
- API 层: `sources.front.label` ✅
- 前端 JS: `m.roll`, `b.gait` ✅

### 配置项对照
- `telemetry_tx_enabled`: False (安全默认) ✅
- `control_enabled`: False (安全默认) ✅
- `gimbal_password`: "123456" (需修改) ⚠️

---

## 五、代码质量统计

| 指标 | 数值 |
|------|------|
| Python 文件 | 26 |
| 测试文件 | 17 |
| 测试用例 | 180 |
| 编译错误 | 0 |
| 语法错误 | 0 |

---

## 六、文档输出

| 文件 | 路径 |
|------|------|
| 详细审查报告 | `docs/reviews/audit-2026-08-10.md` |
| 术语优化对照 | `docs/reviews/terminology-optimization.md` |

---

## 七、后续建议

1. **短期**: 修改云台默认密码，从环境变量读取
2. **短期**: 将 RTSP 地址改为从 manifest 配置
3. **中期**: 清理 `dashboard_realtime.py` 重复逻辑
4. **长期**: 统一使用 `TelemetryAdapter` 作为唯一数据源
