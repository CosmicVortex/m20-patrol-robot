# 文档体系结构

## 当前文档结构

```
docs/
├── 00-index.md              # 文档导航入口
├── 01-overview.md           # 项目概览：目标、范围、当前阶段
├── 02-architecture.md       # 系统架构：主机角色、协议接口、数据边界
├── 03-modules.md            # 模块说明：代码模块职责与接口
├── 04-requirements.md       # 需求清单：编号、状态、验收证据
├── 05-testing.md            # 测试流程：云端验证、部署验证、实机验收
├── 06-deployment.md         # 部署流程：GOS安装、验证、回滚
├── 07-changes.md            # 变更记录：重大修改历史
├── branch-policy.md         # 分支管理策略
├── official-docs-index.md   # 官方资料台账（19份文档索引）
│
├── procedures/              # 现场操作手册
│   ├── operations-manual.md # 操作指令速查（整合自官方文档）
│   ├── deployment-guide.md  # 部署执行手册
│   └── mapping-test.md      # 建图、定位、标点测试
│
├── reviews/                 # 审查记录
│   ├── v121-alignment.md    # V1.2.1协议对齐审查
│   ├── blockers-fixed.md    # 阻塞项修复报告
│   └── comprehensive-audit-20260809.md # 全面代码与文档审查
│
└── archive/                 # 归档文档（不作为当前实施依据）
    ├── legacy/              # 历史执行报告、临时文件
    ├── architecture.md      # 历史架构文档
    └── requirements.md      # 历史需求文档
```

## 官方文档（只读）

共 **19份** 官方文档，存放于 `docs/official/`：

| 类型 | 数量 | 说明 |
|------|------|------|
| PDF | 3 | 产品手册、软件使用手册、软件开发手册 |
| Markdown | 16 | 协议总览、开发指南、教程等 |

详细索引见 [official-docs-index.md](./official-docs-index.md)。

## 文档职责划分

| 文档 | 职责 | 读者 |
|------|------|------|
| `01-overview.md` | 项目背景、目标、范围 | 新成员、管理层 |
| `02-architecture.md` | 系统架构、数据边界 | 架构师、开发者 |
| `03-modules.md` | 模块详细设计 | 开发者 |
| `04-requirements.md` | 需求追踪、验收标准 | PM、测试人员 |
| `05-testing.md` | 测试方法、验证标准 | 测试人员 |
| `06-deployment.md` | 部署步骤、回滚方案 | 运维工程师 |
| `procedures/operations-manual.md` | 现场操作指令速查 | 现场工程师 |
| `procedures/deployment-guide.md` | 详细部署流程 | 部署工程师 |
| `procedures/mapping-test.md` | 建图测试步骤 | 现场工程师 |
| `reviews/*.md` | 审查记录 | 审查人员 |

## 文档编写规范

### 命名规范

- 编号文档：`NN-name.md`（01-07 连续编号）
- 归档文档：`YYYYMMDD-descriptive-name.md`
- 操作手册：`descriptive-name.md`（无编号）
- 审查报告：`review-name-date.md`

### 内容规范

1. **开头**：说明文档目的、适用范围、最后更新日期
2. **正文**：使用表格、代码块、列表，避免大段纯文字
3. **状态标识**：使用图例符号（✅/🟡/🔴/📋）
4. **版本追踪**：变更记录末尾追加，不修改历史

### 禁止项

- 不在文档中嵌入密码、Token、私钥
- 不混入已过时的历史文档内容
- 不在同一位置保留多个重复文档
