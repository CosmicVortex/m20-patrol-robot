# 文档导航

本目录包含项目的所有非官方文档。官方文档（只读）存放在 `docs/official/`。

## 文档索引

| 编号 | 文件名 | 用途 | 读者 |
|------|--------|------|------|
| 00 | [index.md](./index.md) | 导航入口 | 所有人 |
| 01 | [overview.md](./overview.md) | 项目概览：目标、范围、阶段 | 新成员、管理层 |
| 02 | [architecture.md](./architecture.md) | 系统架构、主机角色、协议接口 | 架构师、开发者 |
| 03 | [modules.md](./modules.md) | 模块说明：代码职责与接口 | 开发者 |
| 04 | [requirements.md](./requirements.md) | 需求清单：编号、状态、验收证据 | PM、测试人员 |
| 05 | [testing.md](./testing.md) | 测试流程：云端验证、部署验证 | 测试人员 |
| 06 | [deployment.md](./deployment.md) | 部署流程：GOS安装、验证、回滚 | 运维工程师 |
| 07 | [changes.md](./changes.md) | 变更记录：重大修改历史 | 所有人 |
| 08 | [branch-policy.md](./branch-policy.md) | 分支管理策略 | 开发者 |
| 09 | [official-docs.md](./official-docs.md) | 官方资料台账（19份文档索引） | 所有人 |

## 操作手册

| 文件名 | 用途 | 读者 |
|--------|------|------|
| [procedures/operations-manual.md](./procedures/operations-manual.md) | 现场操作指令速查 | 现场工程师 |
| [procedures/deployment-guide.md](./procedures/deployment-guide.md) | 部署执行手册 | 部署工程师 |
| [procedures/mapping-test.md](./procedures/mapping-test.md) | 建图、定位、标点测试 | 现场工程师 |

## 审查记录

| 文件名 | 内容 |
|--------|------|
| [reviews/20260807-blockers-fixed.md](./reviews/20260807-blockers-fixed.md) | 阻塞项修复报告 |
| [reviews/v121-alignment.md](./reviews/v121-alignment.md) | V1.2.1协议对齐审查 |

## 目录结构

```
docs/
├── index.md                 # 本文件 - 导航入口
├── overview.md              # 项目概览
├── architecture.md          # 系统架构
├── modules.md               # 模块说明
├── requirements.md          # 需求清单
├── testing.md               # 测试流程
├── deployment.md            # 部署流程
├── changes.md               # 变更记录
├── branch-policy.md         # 分支管理策略
├── official-docs.md         # 官方资料台账
│
├── procedures/              # 现场操作手册
│   ├── operations-manual.md # 操作指令速查
│   ├── deployment-guide.md  # 部署执行手册
│   └── mapping-test.md      # 建图测试
│
├── reviews/                 # 审查记录
│   ├── v121-alignment.md    # V1.2.1对齐
│   └── 20260807-blockers-fixed.md # 阻塞项修复
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

## 阅读顺序

1. **新成员**：`overview.md` → `architecture.md`
2. **开发者**：`modules.md` → `requirements.md`
3. **现场工程师**：`procedures/operations-manual.md`
4. **审查人员**：`reviews/` 目录
