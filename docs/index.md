# 文档导航

## 核心文档

| 编号 | 文件名 | 用途 | 读者 |
|------|--------|------|------|
| 01 | [overview.md](./01-overview.md) | 项目概览 | 新成员、管理层 |
| 02 | [architecture.md](./02-architecture.md) | 系统架构 | 架构师、开发者 |
| 03 | [modules.md](./03-modules.md) | 模块说明 | 开发者 |
| 04 | [requirements.md](./04-requirements.md) | 需求清单 | PM、测试人员 |
| 05 | [testing.md](./05-testing.md) | 测试流程 | 测试人员 |
| 06 | [deployment.md](./06-deployment.md) | 部署流程 | 运维工程师 |
| 07 | [changes.md](./07-changes.md) | 变更记录 | 所有人 |
| 08 | [branch-policy.md](./08-branch-policy.md) | 分支策略 | 开发者 |
| 09 | [official-docs.md](./09-official-docs.md) | 官方文档索引 | 所有人 |
| 09 | [09-real-web-integration-contract.md](./09-real-web-integration-contract.md) | 真实Web开发契约 | 开发者 |
| 10 | [10-real-web-progress.md](./10-real-web-progress.md) | 集成进度 | 所有人 |

## 操作手册

| 文件名 | 用途 | 读者 |
|--------|------|------|
| [procedures/operations-manual.md](./procedures/operations-manual.md) | 操作指令速查 | 现场工程师 |
| [procedures/deployment-guide.md](./procedures/deployment-guide.md) | 部署执行手册 | 运维工程师 |
| [procedures/mapping-test.md](./procedures/mapping-test.md) | 建图测试 | 现场工程师 |
| [procedures/real-web-integration-preflight.md](./procedures/real-web-integration-preflight.md) | 真实Web联调前置采集 | 运维工程师 |

## 目录结构

```
docs/
├── index.md                 本文件
├── 01-overview.md           项目概览
├── 02-architecture.md       系统架构
├── 03-modules.md            模块说明
├── 04-requirements.md       需求清单
├── 05-testing.md            测试流程
├── 06-deployment.md         部署流程
├── 07-changes.md            变更记录
├── 08-branch-policy.md      分支策略
├── 09-official-docs.md      官方文档索引
├── 09-real-web-integration-contract.md  真实Web开发契约
├── 10-real-web-progress.md  集成进度
│
├── procedures/              操作手册
│   ├── operations-manual.md
│   ├── deployment-guide.md
│   ├── mapping-test.md
│   └── real-web-integration-preflight.md
│
└── official/                官方文档（只读）
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
