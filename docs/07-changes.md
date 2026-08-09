# 07 — 变更记录

## 2026-08-09 — 文档规范化与代码清理

- 清理根目录冗余文件，归档至 archive/
- 重命名文档统一编号
- 替换 print 为 logger（server.py、dashboard_realtime.py、dashboard_simple.py）
- 更新 navigation API TODO 说明
- 修复 telemetry.py bug（`status_type` → `kind`）
- 恢复 NOS IP 为官方确认值 `10.21.31.106`
- 169 测试全部通过

## 2026-08-07 — V0.5 代码核查

- 修复测试文件截断
- 修复 trailing whitespace
- 更新 `connect()` 参数
- 优化部署脚本

## 2026-08-06 — V0.4 功能增强

- 新增 TelemetryAdapter（真实状态订阅）
- 新增 RealTimeDashboard
- 新增 NavigationService（导航控制）
- 114 passed

## 2026-08-05 — V0.1 初始基线

- APDU/ASDU 编解码
- 状态解析模块
- TCP 客户端 + 门禁
- 导航报文构造
- 模拟仪表盘
- 安装/回滚脚本
