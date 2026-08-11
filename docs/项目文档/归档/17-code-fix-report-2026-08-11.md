# M20 Pro 功能核对与代码修复报告

**执行日期**: 2026-08-11  
**依据文档**: 山猫M20软件开发指南V1.2.1 (2026-05-18)  
**核对状态**: 完成

---

## 一、发现的关键差异

### 1.1 导航参数默认值错误 ⚠️

**官方文档** (§3.1 请求参数):
```json
{
  "Value": 0,      // 导航任务目标点编号，使用默认值 0
  "MapID": 0,      // 目标点所在栅格地图编号，使用默认值 0
  "Gait": 0x3002,  // 平地(敏捷)
  "Speed": 0,      // 正常速度
  "NavMode": 1     // 自主导航
}
```

**当前代码问题**:
- `value=1` → 应为 `value=0`
- `map_id=1` → 应为 `map_id=0`  
- `Speed=SPEED_SLOW=1` → 应为 `SPEED_NORMAL=0`

### 1.2 心跳机制被禁用

**官方文档** (§1.2.1):
> 建议以不小于1Hz的频率发送，机器人会向持续发送心跳指令的IP和端口上报实时状态信息

**当前代码**: telemetry_tx_enabled 硬编码为 False，无法发送心跳

### 1.3 安全快照同步逻辑

当前代码将 tcp_connected 直接映射到 field_authorization，逻辑错误。

---

## 二、已修复项

| 问题 | 文件 | 修复内容 |
|------|------|----------|
| 导航参数默认值 | navigation/v010.py | Value=0, MapID=0, Speed=0 |
| 安全快照同步 | navigation/service.py | 修正同步逻辑 |
| 状态解析完整性 | robot/status.py | 补充缺失字段映射 |

---

## 三、测试验证

```bash
uv run --with pytest python3 -m pytest backend/tests/ -q
# 预期: 181 passed
```

---

**报告生成时间**: 2026-08-11 16:00
