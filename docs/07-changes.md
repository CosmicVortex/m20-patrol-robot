# 变更记录

## 2026-08-09 — 文档规范化

- 清理冗余文档，归档临时文件
- 重命名文档统一编号
- 新建操作手册整合现场指令
- 修复 telemetry.py bug（`status_type` → `kind`）

## 2026-08-07 — V0.5 代码核查

- 修复测试文件截断
- 修复 trailing whitespace
- 添加 read_only 参数
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
