# 文档导航

## 文档索引

| 编号 | 文件名 | 用途 |
|------|--------|------|
| 01 | [overview.md](./overview.md) | 项目概览 |
| 02 | [architecture.md](./architecture.md) | 系统架构 |
| 03 | [modules.md](./modules.md) | 模块说明 |
| 04 | [requirements.md](./requirements.md) | 需求清单 |
| 05 | [testing.md](./testing.md) | 测试流程 |
| 06 | [deployment.md](./deployment.md) | 部署流程 |
| 07 | [changes.md](./changes.md) | 变更记录 |
| 08 | [branch-policy.md](./branch-policy.md) | 分支策略 |
| 09 | [official-docs.md](./official-docs.md) | 官方文档索引 |

## 操作手册

| 文件名 | 用途 |
|--------|------|
| [procedures/operations-manual.md](./procedures/operations-manual.md) | 操作指令速查 |
| [procedures/deployment-guide.md](./procedures/deployment-guide.md) | 部署执行手册 |
| [procedures/mapping-test.md](./procedures/mapping-test.md) | 建图测试 |

## 审查记录

| 文件名 | 内容 |
|--------|------|
| [reviews/v121-alignment.md](./reviews/v121-alignment.md) | V1.2.1 协议对齐 |
| [reviews/20260807-blockers-fixed.md](./reviews/20260807-blockers-fixed.md) | 阻塞项修复 |

## 目录结构

```
docs/
├── index.md                 # 本文件
├── overview.md              # 项目概览
├── architecture.md          # 系统架构
├── modules.md               # 模块说明
├── requirements.md          # 需求清单
├── testing.md               # 测试流程
├── deployment.md            # 部署流程
├── changes.md               # 变更记录
├── branch-policy.md         # 分支策略
├── official-docs.md         # 官方文档索引
│
├── procedures/              # 操作手册
│   ├── operations-manual.md
│   ├── deployment-guide.md
│   └── mapping-test.md
│
├── reviews/                 # 审查记录
│   ├── v121-alignment.md
│   └── 20260807-blockers-fixed.md
│
└── official/                # 官方文档（只读）
    ├── 3份 PDF
    └── 16份 Markdown
```

## 文档状态图例

| 符号 | 含义 |
|------|------|
| ✅ | 已实现且验证 |
| 🟡 | 部分实现，需现场验证 |
| 🔴 | 未实现 |
| 📋 | 需现场执行 |
