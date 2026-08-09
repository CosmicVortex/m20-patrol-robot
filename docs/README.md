# 项目文档

本目录保留当前有效文档；历史计划和审查模板放在 `docs/archive/`，不作为当前实施依据。

## 当前文档

| 文件 | 用途 | 状态 |
|---|---|---|
| `00-index.md` | 文档导航入口 | 当前基线 |
| `01-overview.md` | 项目概览：目标、范围、当前阶段 | 当前基线 |
| `02-architecture.md` | 系统架构：当前实现、目标边界、数据边界 | 当前基线 |
| `03-modules.md` | 模块说明：每个代码模块的职责与接口 | 当前基线 |
| `04-requirements.md` | 需求清单：编号、状态、验收证据、放行条件 | 当前基线 |
| `05-testing.md` | 测试流程：本地验证、部署验证、实机验收 | 当前基线 |
| `06-deployment.md` | 部署流程：GOS安装、验证、回滚 | 当前基线 |
| `07-changes.md` | 变更记录：重大修改历史 | 当前基线 |
| `official-docs-review.md` | 官方资料台账与差异记录 | 当前基线 |
| `procedures/mapping-test.md` | 建图与定位测试操作手册 | 现场操作说明 |
| `procedures/office-acceptance.md` | [测试场地]阶段验收测试 | 现场操作说明 |
| `reviews/v121-alignment.md` | V1.2.1代码对齐审查 | 审查记录 |
| `reviews/blockers-fixed.md` | 阻塞项修复报告 | 审查记录 |

## 官方资料库

共 **19份**（3 PDF + 16 Markdown），详细索引见 [official-docs-review.md](./official-docs-review.md)。

## 归档文档

| 文件 | 说明 |
|---|---|
| `archive/plans/phase1-navigation-web.md` | 第一阶段实施计划（历史） |
| `archive/review/project-multidimensional-review-prompt.md` | 多维度审查提示词（历史） |

## 编写规则

- 文件版本和机器人软件/固件版本分开记录；
- 地址、端口、目录和命令标为文档事实或现场事实；
- 现场操作必须有前置条件、通过标准、停止条件和结果栏；
- 同类教程只保留一份当前版本；
- 不在仓库保存密码、Token、地图、视频和未脱敏日志。
