# 00 — 文档导航

本目录包含项目的所有非官方文档。官方文档（只读）存放在 `docs/official/`。

## 快速入口

| 你想知道什么 | 看这里 |
|---|---|
| 项目是什么、当前阶段、安全规则 | [01-overview.md](./01-overview.md) |
| 系统架构、主机角色、协议接口 | [02-architecture.md](./02-architecture.md) |
| 每个代码模块的作用 | [03-modules.md](./03-modules.md) |
| 需求清单、验收条件、当前能力 | [04-requirements.md](./04-requirements.md) |
| 如何测试、验证 | [05-testing.md](./05-testing.md) |
| 如何部署、停止、回滚 | [06-deployment.md](./06-deployment.md) |
| 变更记录、版本历史 | [07-changes.md](./07-changes.md) |
| **[现场操作手册]** | **[procedures/operations-manual.md](./procedures/operations-manual.md)** |
| 部署执行手册 | [procedures/deployment-guide.md](./procedures/deployment-guide.md) |
| 建图、定位、标点测试 | [procedures/mapping-test.md](./procedures/mapping-test.md) |
| V1.2.1 对齐状态 | [reviews/v121-alignment.md](./reviews/v121-alignment.md) |
| 阻塞项修复记录 | [reviews/blockers-fixed.md](./reviews/blockers-fixed.md) |
| 全面审查报告 | [reviews/comprehensive-audit-20260809.md](./reviews/comprehensive-audit-20260809.md) |
| 官方资料台账 | [official-docs-index.md](./official-docs-index.md) |

## 目录结构

```
docs/
├── 00-index.md              # 本文件 - 导航入口
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
├── procedures/              # 现场操作手册
│   ├── operations-manual.md # 操作指令速查（新）
│   ├── deployment-guide.md  # 部署执行手册
│   └── mapping-test.md      # 建图测试
│
├── reviews/                 # 审查记录
│   ├── v121-alignment.md    # V1.2.1对齐
│   ├── blockers-fixed.md    # 阻塞项修复
│   └── comprehensive-audit-20260809.md # 全面审查
│
└── archive/                 # 归档文档（不作为当前依据）
    ├── legacy/              # 历史执行报告与临时文件
    ├── architecture.md      # 历史架构文档
    └── requirements.md      # 历史需求文档
```

## 文档状态图例

| 符号 | 含义 |
|---|---|
| ✅ | 已实现且验证 |
| 🟡 | 部分实现，需现场验证 |
| 🔴 | 未实现 |
| 📋 | 需现场执行 |

## 阅读顺序

1. **新成员**：先读 `01-overview.md`，再读 `02-architecture.md`
2. **开发者**：重点读 `03-modules.md` 和 `04-requirements.md`
3. **现场工程师**：重点读 `procedures/operations-manual.md` 和 `procedures/deployment-guide.md`
4. **审查人员**：重点读 `reviews/` 目录

## 文档更新规则

- 变更必须关联需求编号（R-01 至 R-10）
- 新增功能需更新对应模块文档
- 部署步骤变更需同步更新操作手册
- 归档文档不得混入当前工作文档
