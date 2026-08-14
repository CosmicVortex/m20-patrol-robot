# M20 Pro 项目全面优化提示词

## 项目概述
- **项目名称**: M20 Pro 巡逻机器人系统
- **部署门店**: 中升之星奔驰 4S店
- **机器人型号**: 山猫 M20 Pro（无 PRO/STD 区分）
- **工作目录**: `/opt/data/m20-patrol-robot`
- **当前状态**: 🟡 offline_verified（待GOS实机验证）
- **最新提交**: `7bccd30`（Web UI状态管理修复）
- **总技能数**: 508个（已分析）

---

## 可用技能清单（深度分析结果）

### 🎯 核心项目技能（M20专用）- 10个
| 技能名称 | 用途 | 优先级 |
|----------|------|--------|
| `m20-code-review-fix` | 代码审查与P0/P1/P2问题分类 | 🔴 高 |
| `m20-gos-deployment` | GOS离线部署、Python 3.8兼容 | 🔴 高 |
| `m20-patrol-deployment` | 一键部署流程、回滚机制 | 🔴 高 |
| `m20-basic-server-connection` | TCP心跳、遥测数据获取 | 🔴 高 |
| `m20-auth-fix` | 匿名认证Bug修复 | 🟡 中 |
| `m20-document-quality` | 文档质量提升流程 | 🟡 中 |
| `m20-data-consistency-audit` | 前后端字段一致性检查 | 🟡 中 |
| `m20-official-doc-alignment` | 协议与V1.2.1手册对齐 | 🟡 中 |
| `m20-config-verification` | 配置验证（密码/RTSP/Manifest） | 🟡 中 |
| `m20-ui-optimization` | Web UI优化（SVG/玻璃态） | 🟡 中 |

### 🛠️ 通用开发技能 - 5个
| 技能名称 | 用途 | 优先级 |
|----------|------|--------|
| `code-reviewer` | 代码审查通用模式 | 🔴 高 |
| `python` | Python编码规范（PEP 8） | 🔴 高 |
| `protocol-audit` | 协议实现合规性审计 | 🔴 高 |
| `web-ui-review` | Web UI代码审查 | 🟡 中 |
| `ui-depth-audit-checklist` | UI深度审查7维度 | 🟡 中 |

### 📝 文档与测试技能 - 4个
| 技能名称 | 用途 | 优先级 |
|----------|------|--------|
| `markdown-lint` | Markdown格式检查 | 🟢 低 |
| `api-documentation` | API文档生成 | 🟢 低 |
| `test-report-generator` | 测试报告生成 | 🟢 低 |
| `readme-generator` | README自动生成 | 🟢 低 |

### 🚀 部署与运维技能 - 4个
| 技能名称 | 用途 | 优先级 |
|----------|------|--------|
| `deployment` | 部署流程管理 | 🔴 高 |
| `static-site-hosting` | 静态网站托管 | 🟡 中 |
| `vulnerability-scanner` | 安全漏洞扫描 | 🟡 中 |
| `performance-test-runner` | 性能测试 | 🟡 中 |

### 📊 项目管理技能 - 3个
| 技能名称 | 用途 | 优先级 |
|----------|------|--------|
| `kanban-board` | 看板任务管理 | 🟡 中 |
| `gantt-chart` | 甘特图进度可视化 | 🟡 中 |
| `retrospective` | 项目回顾与改进 | 🟢 低 |

**总计适用技能**: 26个（占总技能数5.1%）

---

## 分阶段优化工作流

### 阶段一：现状审计（Phase 1 Audit）
**目标**: 全面评估项目当前状态，识别改进机会

**执行命令**:
```bash
# 1. 代码质量审计
PYTHONPATH=. uv run --with pytest pytest backend/tests/ -q
python3 -m compileall -q backend/
python3 -c "from backend.app.server import M20WebServer; print('OK')"

# 2. 门禁顺序验证
python3 -c "import inspect; from backend.app.api.handlers import EmergencyStopHandler, NavigationTaskHandler; from backend.app.motion.handlers import MotionStateHandler; handlers = [('EmergencyStop', EmergencyStopHandler), ('NavTask', NavigationTaskHandler), ('MotionState', MotionStateHandler)]; [print(f'✓ {name}' if (rpos := s.find('read_only_mode')) >= 0 and (apos := s.find('_authenticate')) >= 0 and rpos < apos else f'✗ {name}') or exec('') for name, cls in handlers for s in [inspect.getsource(cls.do_POST)]]"

# 3. 数据一致性检查
grep -rn "battery_percent\|battery_left\|battery_right" docs/website/js/state-manager.js
grep -rn "BatteryLevel" backend/app/robot/status.py

# 4. 文档质量检查
grep -rn "TODO\|FIXME" docs/ --include="*.md"
grep -rn "S10\|s10" docs/ README.md --include="*.md"
```

---

### 阶段二：代码审查与修复（Phase 2 Code Review）
**目标**: 系统性审查后端代码，修复P0/P1问题

**使用技能**: `m20-code-review-fix`, `code-reviewer`, `python`, `protocol-audit`

**审查维度**:
1. **安全性检查**: read_only_mode前置、认证中间件、无明文密码、WebSocket握手认证
2. **数据流检查**: 遥测字段映射、电池数据传播、导航安全快照、云台状态更新
3. **资源管理**: WebSocket生命周期、视频转码进程清理、云台适配器释放
4. **Python 3.8兼容性**: 类型注解、UTC导入、日志格式

---

### 阶段三：Web UI优化（Phase 3 UI Optimization）
**目标**: 优化前端界面，修复数据流问题

**使用技能**: `m20-ui-optimization`, `web-ui-review`, `ui-depth-audit-checklist`

**已完成（2026-08-14）**:
- ✅ StateManager初始化tasks和inspectionPoints
- ✅ 添加updateTasks()和updateInspectionPoints()方法
- ✅ fetchInspectionPoints()结果写入state
- ✅ SVG图标替换、玻璃态效果、电池环形仪表

**待验证**:
- 表单完整性（add-device-form等）
- 无障碍访问检查
- 颜色对比度WCAG AA

---

### 阶段四：文档体系建设（Phase 4 Documentation）
**目标**: 建立标准化、高质量的文档体系

**使用技能**: `m20-document-quality`, `m20-data-consistency-audit`, `m20-official-doc-alignment`

**检查清单**:
- 机型名称统一（M20 Pro vs S10）
- 测试数量同步（当前232 passed）
- API路径与router.py一致
- 无明文密码暴露
- 命名规范（编号前缀）

---

### 阶段五：部署验证准备（Phase 5 Deployment Readiness）
**目标**: 确保部署包完整、可复现、可回滚

**使用技能**: `m20-gos-deployment`, `m20-patrol-deployment`, `protocol-audit`

**检查清单**:
- 包名固定为m20-patrol-robot.zip
- SHA-256清单生成
- FFmpeg RTSP检测正确
- 回滚机制验证

---

## 优化执行合同

### 每次代码修改后必须:
1. 编译检查: `python3 -m compileall -q backend/`
2. 全量测试: `PYTHONPATH=. uv run --with pytest pytest backend/tests/ -q`
3. 委派独立子代理只读复审（最多3轮）
4. 必须修复项先处理再提交

### Git提交规范:
```bash
git commit -m "fix: [模块] 修复[问题描述]

验证：
• [测试数量]测试通过 ✅"
```

---

## 已知限制与政策

### 开发阶段允许:
- 明文密码 `123456`（演示阶段）
- 站点名称硬编码
- 默认云台IP地址

### 禁止行为:
- ❌ 虚构接口或功能完成度
- ❌ 将离线测试表述为实机验证
- ❌ 使用废弃地址 `10.21.31.101`
- ❌ 发送控制指令除非明确授权

---

**提示词版本**: V2.0  
**生成日期**: 2026-08-14  
**依据技能**: 26个核心技能（从508个中筛选）
