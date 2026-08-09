# 变更记录

## 2026-08-09 — 文档架构重构与脱敏

### 变更内容

1. **文档结构调整**
   - 归档重复的执行报告（5份）至 `docs/archive/legacy/`
   - 合并 `执行报告-20260809-全面审查.md` 到 `reviews/comprehensive-audit-20260809.md`
   - 新增 `reviews/comprehensive-audit-20260809.md` 作为当前审查基线

2. **脱敏处理**
   - 所有具体企业名称替换为占位符
   - 地点信息统一使用 `[测试场地]`、`[客户场地]` 占位

3. **Bug修复**
   - 修复 `telemetry.py` 中 `StatusResult.status_type` 应为 `kind` 的阻塞性 Bug（commit `e1e75e1`）

4. **测试**
   - 114 passed（Python 3.13 和 3.8.10 均通过）

---

## 2026-08-07 — V0.5 代码核查与部署优化

### 发现的问题

1. **测试文件被截断**
   - `backend/tests/test_basic_client.py` 从 71 行被截断为 6 行
   - 已恢复完整测试文件

2. **代码格式问题**
   - `basic_client.py` 存在 trailing whitespace
   - 已修复

### 官方协议一致性核查

与《山猫M20软件开发指南》V1.2.1 逐项核对：

| 核对项 | 状态 |
|--------|------|
| 协议头部结构（16字节） | ✅ 完全一致 |
| 同步字 `EB 91 EB 90` | ✅ 正确 |
| 字节序（小端） | ✅ 正确 |
| 消息类型定义 | ✅ 正确 |
| 导航参数常量 | ✅ 正确 |
| 安全门禁实现 | ✅ 正确 |
| 心跳频率（1Hz） | ✅ 符合要求 |
| 断连检测（3秒） | ✅ 符合要求 |

### 代码改进

1. **添加 read_only 参数**
   - `BasicServerClient.connect()` 新增 `read_only: bool = False`
   - `read_only=True` 允许只读连接（状态订阅），不通过 control_enabled 门禁
   - `TelemetryAdapter` 正确传递 `read_only=True`

2. **添加 Python 3.8 兼容性**
   - 所有模块添加 UTC 兼容处理（try/except ImportError）
   - 创建 `dashboard_simple.py`，仅使用标准库

3. **优化部署脚本**
   - 使用 `$HOME` 替代硬编码路径
   - 添加健康检查循环（最多等待10秒）
   - 支持 python-unzip 备选解压

### 测试结果

```
Python 3.13 与 Python 3.8.10：114 passed
```

---

## 2026-08-06 — V0.4 真实状态订阅、视频接入、导航控制

### 代码新增

- 新增 `backend/app/robot/telemetry.py`：TelemetryAdapter 类
- 新增 `backend/app/dashboard_realtime.py`：实时仪表盘
- 新增 `backend/app/navigation/service.py`：导航控制服务
- 新增 `backend/app/navigation/ws_handler.py`：导航 WebSocket 处理器
- 新增 `deploy/systemd/m20-patrol-realtime.service`：systemd 服务模板

### 功能说明

**TelemetryAdapter（真实状态订阅）**：
- 自动连接到 AOS basic_server TCP 30001
- 生产只读模式不发送心跳，`TELEMETRY_TX_ENABLED=false`
- 接收并解析状态消息
- 断线自动重连

**NavigationService（导航控制）**：
- Web UI 授权机制
- 安全门控检查
- 审计日志记录

---

## 2026-08-06 — V0.3 文档架构重构

### 文档架构

- 新增 `01-overview.md`：项目概览
- 新增 `03-modules.md`：代码模块说明
- 新增 `05-testing.md`：测试流程
- 新增 `06-deployment.md`：部署流程
- 新增 `07-changes.md`：变更记录
- 新建 `procedures/` 目录：现场操作手册
- 新建 `reviews/` 目录：审查记录
- 归档历史文档到 `docs/archive/`

---

## 2026-08-05 — V0.1 初始基线

### 代码

- 完成 APDU/ASDU 编解码（frame.py + messages.py）
- 完成状态解析模块（status.py）
- 完成 TCP 客户端+门禁（basic_client.py）
- 完成导航报文构造+安全门控（v010.py）
- 完成模拟仪表盘（dashboard.py）
- 完成安装/回滚脚本

### 阻塞项修复

1. message_id 关联
2. control_enabled 门禁
3. 安装回滚脚本
