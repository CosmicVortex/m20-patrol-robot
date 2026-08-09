# 文档体系结构

## 目录结构

```
docs/
├── index.md                 # 文档导航入口
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
│   ├── v121-alignment.md    # V1.2.1协议对齐
│   └── 20260807-blockers-fixed.md # 阻塞项修复
│
└── official/                # 官方文档（只读，19份）
    ├── 山猫M20系列软件开发手册V0.1.0.pdf
    ├── 山猫M20 Pro软件使用手册V0.0.1.pdf
    ├── 山猫M20 Pro产品手册 V1.1.0.pdf
    └── 16份 Markdown 文档
```

## 文档职责划分

| 文档 | 职责 | 读者 |
|------|------|------|
| `index.md` | 导航入口 | 所有人 |
| `overview.md` | 项目背景、目标、范围 | 新成员、管理层 |
| `architecture.md` | 系统架构、数据边界 | 架构师、开发者 |
| `modules.md` | 模块详细设计 | 开发者 |
| `requirements.md` | 需求追踪、验收标准 | PM、测试人员 |
| `testing.md` | 测试方法、验证标准 | 测试人员 |
| `deployment.md` | 部署步骤、回滚方案 | 运维工程师 |
| `changes.md` | 变更记录 | 所有人 |
| `branch-policy.md` | 分支管理策略 | 开发者 |
| `official-docs.md` | 官方文档索引 | 所有人 |
| `procedures/*.md` | 现场操作手册 | 现场工程师 |
| `reviews/*.md` | 审查记录 | 审查人员 |

## 文档更新规则

1. **变更必须关联需求编号**（R-01 至 R-10）
2. **新增功能需更新**对应模块文档
3. **部署步骤变更**需同步更新操作手册
4. **归档文档**不得混入当前工作文档

## 命名规范

- 编号文档：`NN-name.md`（01-09 连续编号）
- 操作手册：`procedures/descriptive-name.md`
- 审查记录：`reviews/v121-alignment.md` 或 `reviews/YYYYMMDD-descriptive.md`
- 归档文件：`archive/legacy/YYYYMMDD-descriptive.md`
