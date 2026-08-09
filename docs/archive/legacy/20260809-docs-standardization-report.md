# 文档体系规范化完成报告

**时间**: 2026-08-09  
**提交**: `c0bdff7`

---

## 执行摘要

| 项目 | 结果 |
|------|------|
| 归档冗余文档 | 2个 procedures + 4个 memory 文件 |
| 重命名文档 | 1个（official-docs-review → official-docs-index） |
| 新建操作手册 | 1个（operations-manual.md） |
| 更新索引 | 2个（00-index.md, README.md） |
| 测试验证 | 114 passed ✅ |

---

## 文档清理清单

### 归档的文件

| 原文件 | 归档位置 | 原因 |
|--------|----------|------|
| `procedures/mobaxterm-deployment.md` | `archive/legacy/` | 内容已整合到 deployment-guide.md |
| `procedures/office-acceptance.md` | `archive/legacy/` | 建议合并到 mapping-test.md |
| `memory/index.md` | `archive/legacy/` | 临时执行索引，已归档 |
| `memory/checkpoints/*.json` | `archive/legacy/checkpoints/` | 临时检查点 |
| `memory/tasks/T1-*.md` | `archive/legacy/tasks/` | 临时任务报告 |
| `memory/tasks/T2-*.md` | `archive/legacy/tasks/` | 临时任务报告 |

### 重命名的文件

| 原文件名 | 新文件名 | 原因 |
|----------|----------|------|
| `official-docs-review.md` | `official-docs-index.md` | 统一命名规范 |

### 新建的文件

| 文件 | 说明 |
|------|------|
| `procedures/operations-manual.md` | 现场操作手册，整合所有官方文档关键操作指令 |

---

## 文档体系结构

```
docs/
├── 00-index.md              # 导航入口
├── 01-overview.md           # 项目概览
├── 02-architecture.md       # 系统架构
├── 03-modules.md            # 模块说明
├── 04-requirements.md       # 需求清单
├── 05-testing.md            # 测试流程
├── 06-deployment.md         # 部署流程
├── 07-changes.md            # 变更记录
├── branch-policy.md         # 分支管理策略
├── official-docs-index.md   # 官方资料台账
│
├── procedures/              # 现场操作手册（3个）
│   ├── operations-manual.md # ⭐ 操作指令速查（新）
│   ├── deployment-guide.md  # 部署执行手册
│   └── mapping-test.md      # 建图测试
│
├── reviews/                 # 审查记录（3个）
│   ├── v121-alignment.md
│   ├── blockers-fixed.md
│   └── comprehensive-audit-20260809.md
│
└── archive/                 # 归档文档
    ├── legacy/              # 历史执行报告与临时文件
    ├── architecture.md
    └── requirements.md
```

---

## 新建操作手册内容

`procedures/operations-manual.md` 整合了官方文档中的关键操作指令：

### 1. 主机连接
- SSH 连接到 NOS/GOS
- 端口信息表

### 2. 版本确认
- 查询固件版本命令
- APP 版本记录方法

### 3. 网络配置
- 主机身份确认
- 网络连通性测试
- 禁用旧地址检查

### 4. 建图操作
- 建图前安全准备
- 启动/停止建图命令
- 地图备份与 SHA-256 记录

### 5. 定位核验
- RViz 定位检查
- APP 标点工具使用

### 6. 状态监控
- Web API 查询命令
- 状态判定标准
- 系统服务状态检查

### 7. 视频接入
- RTSP 地址表
- 视频流测试命令

### 8. 故障排查
- 服务无法启动
- 遥测无数据
- 视频无响应
- 定位异常

### 附录：快速命令速查表

| 任务 | 命令 |
|------|------|
| SSH 到 NOS | `ssh user@13.21.31.106` |
| 查询固件版本 | `cat /var/opt/robot/release_note.json` |
| 启动建图 | `sudo drmap mapping -n <名称>` |
| 打包地图 | `drmap pack` |
| 部署系统 | `bash deploy/scripts/deploy-readonly.sh --one-shot` |
| 回滚系统 | `bash deploy/scripts/deploy-readonly.sh --rollback <SHA>` |

---

## 文档改进说明

### 1. 命名规范化
- 统一使用小写+连字符命名
- 归档文档使用前缀 `YYYYMMDD-`
- 操作手册使用描述性名称

### 2. 内容去重
- 归档重复的执行报告
- 合并相似的操作文档
- 保留唯一权威版本

### 3. 可读性提升
- 操作手册按场景分类
- 快速命令速查表便于现场使用
- 表格替代大段纯文字

### 4. 结构清晰
- 编号文档负责核心内容
- procedures/ 存放操作手册
- reviews/ 存放审查记录
- archive/ 存放历史归档

---

## 验证

```bash
# 测试通过
PYTHONPATH=. uv run --with pytest pytest -q
# 114 passed

# 文档文件数
find docs -name "*.md" -not -path "*/official/*" | wc -l
# 21 files（当前有效文档）
```

---

**报告生成**: 技术主开发智能体
