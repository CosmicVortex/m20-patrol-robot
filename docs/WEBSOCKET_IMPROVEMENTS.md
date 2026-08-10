# M20 Pro Web界面改进建议

## 当前状态分析

### 已实现功能
| 功能 | 状态 | 文件 |
|------|------|------|
| 状态订阅 | ✅ | `robot/telemetry.py` |
| 导航API | ✅ | `api/handlers.py` (Navigation*) |
| 视频管理 | 🟡 | `video/stream_manager.py` (未接入dashboard) |
| 基础监控页面 | ✅ | `dashboard_realtime.py` |
| 认证系统 | ✅ | `auth/middleware.py` |

### 缺失功能（参考图片）

#### P0 - 核心功能
| 功能 | 说明 | 依赖 |
|------|------|------|
| 3D数字孪生地图 | 工厂平面图+建筑+路线+机器人位置 | 现场地图包、坐标标定 |
| 多相机视频墙 | 4路RTSP实时画面 | RTSP可达性确认、编码格式 |
| 巡检统计卡片 | 在线数、圈数、覆盖率、工单 | telemetry扩展 |

#### P1 - 重要功能
| 功能 | 说明 | 依赖 |
|------|------|------|
| 实时数据面板 | 当前位置、下一点位、检测详情 | 导航状态数据 |
| 改进异常显示 | 带上下文的告警（温度偏差、历史基线） | 异常数据解析 |
| 导航控制UI | 单点导航提交、取消按钮 | 导航API已实现 |

#### P2 - 增强功能
| 功能 | 说明 | 依赖 |
|------|------|------|
| 轨迹回放 | 时间线+进度展示 | 轨迹数据存储 |
| AI告警 | 温度异常检测、历史基线对比 | 历史数据 |
| 一键应急巡检 | 紧急按钮 | 导航控制 |

#### P3 - 可选功能
| 功能 | 说明 | 依赖 |
|------|------|------|
| 工单管理 | 待处理工单、已派单 | 数据库 |
| 设备档案 | 机器人信息管理 | 配置数据 |
| 系统设置 | 参数配置 | 管理权限 |

---

## 立即可实现（本周）

### 1. 统计卡片

**位置**：`dashboard_realtime.py` 顶部

**数据源**：扩展 `telemetry.py` 的 `get_status_payload()`

```python
# telemetry.py 添加
"inspection_stats": {
    "laps_today": 0,          # 从nav_status计算
    "coverage_rate": 0.0,     # 从position计算
    "distance_km": 0.0,       # 累计距离
    "anomaly_count": len(errors),
}
```

**UI实现**：在dashboard中添加4个统计卡片
- 机器人状态（在线/离线）
- 今日巡逻圈数
- 覆盖率
- 异常数量

### 2. 实时数据面板

**位置**：dashboard右侧或底部

**数据源**：
- 当前位置：`position.roll/pitch/yaw`
- 下一点位：`nav_status.next_waypoint`
- 检测详情：从异常数据解析温度信息

### 3. 改进异常显示

**当前**：仅显示error_code和component

**改进**：解析异常数据，显示：
- 异常级别（info/warn/critical）
- 异常来源（温度、震动、位置等）
- 当前值 vs 历史基线
- 偏差百分比

---

## 待现场数据实现

### 1. 3D数字孪生地图

**技术方案**：
- 使用Three.js渲染工厂3D模型
- 或简化版：Canvas 2D地图 + 路线动画
- 数据来源：NOS地图包、现场地图图片

**前置条件**：
- 获取奔驰4S店现场地图图片
- 确认地图包格式和坐标系
- 标定关键点位（配电柜、空压站等）

### 2. 视频墙集成

**技术方案**：
- 使用`stream_manager.py`的RTSP管理
- WebSocket推送视频帧
- 浏览器端使用`<video>`标签播放

**前置条件**：
- 确认RTSP地址格式
- 确认编码格式（H.264/H.265）
- 确认分辨率和帧率

---

## 实现优先级建议

```
优先级1（本周）：
  - 统计卡片（扩展telemetry + 更新dashboard）
  - 改进异常显示（解析error数据）
  - 实时数据面板（展示position/nav_status）

优先级2（下周）：
  - 视频墙集成（需RTSP确认）
  - 导航控制UI（基于已实现的API）

优先级3（待现场数据）：
  - 3D地图（需地图包）
  - 轨迹回放（需数据存储）
  - AI告警（需历史数据）
```

---

## 代码修改清单

### 立即修改
1. `backend/app/robot/telemetry.py` - 扩展get_status_payload()添加inspection_stats
2. `backend/app/dashboard_realtime.py` - 添加统计卡片UI
3. `backend/app/api/handlers.py` - 确保navigation API返回完整数据

### 待实现
1. `backend/app/video/dashboard_video.py` - 视频墙组件
2. `backend/app/map/` - 地图渲染模块
3. `backend/app/tracking/` - 轨迹存储和回放

---

## 测试验证

```bash
# 运行测试
PYTHONPATH=. uv run --with pytest pytest -q

# 验证API
curl http://10.21.31.104:8080/api/v1/status/latest
curl http://10.21.31.104:8080/api/v1/navigation/status
```

---

## 总结

**当前实现已具备基础框架**：
- ✅ 状态订阅系统
- ✅ 导航控制API
- ✅ 视频管理模块
- ✅ 认证系统

**需要补充的核心功能**：
1. 统计卡片（本周可完成）
2. 改进异常显示（本周可完成）
3. 实时数据面板（本周可完成）

**需要现场数据的增强功能**：
- 3D地图（待地图包）
- 视频墙（待RTSP确认）
- AI告警（待历史数据）

**建议立即开始**：统计卡片 + 异常显示改进，预计1-2天完成。
