# P1-1: 修正loop_count数据流

**问题**: `inspection_stats.laps_today` 始终返回0

**根因**: 
- `nav_status` 字段由 Type=1007 Command=1 消息填充
- `LoopCnt` 字段仅在 Type=1007 Command=3 消息中出现
- 两种消息类型写入不同字段，导致读取失败

**文件**: `backend/app/robot/telemetry.py`

**修改位置**: `_update_snapshot_inner` 方法

**修改内容**:
```python
# 在 _update_snapshot_inner 方法中添加
elif kind == "navigation_abnormal":
    self._snapshot.nav_status = data.get("nav_status", {})
```

**验证**:
```python
from backend.app.robot.status import parse_status_message
from backend.app.protocol.messages import PatrolMessage

# 测试navigation_abnormal解析
result = parse_status_message(PatrolMessage(1007, 3, '2026-08-06', {
    'NavStatus': {'LoopCnt': 5, 'ErrorCode': 0}
}))
assert result.kind == "navigation_abnormal"
assert result.data["nav_status"]["loop_count"] == 5
```
