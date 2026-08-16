# 贡献指南

> 欢迎为 M20 Pro 巡逻机器人系统做出贡献！本文档说明如何参与项目开发。

---

## 开发环境

### 前置要求

- Python 3.8+（目标环境为 3.8.10）
- uv（Python包管理器）
- pytest（测试框架）

### 本地开发

```bash
# 克隆仓库
git clone <repository-url>
cd m20-patrol-robot

# 运行测试
PYTHONPATH=. uv run --with pytest pytest backend/tests/ -q

# 启动服务（本地调试）
./start.sh
```

---

## 代码规范

### Python 风格

- 遵循 PEP 8 编码规范
- 使用 `from __future__ import annotations` 兼容 Python 3.8
- 类型注解：所有函数参数和返回值需标注类型
- 日志：使用 `logging.getLogger(__name__)`，不使用 print

### 提交信息

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>: <subject>

[optional body]

# 示例
fix: 修复云台move接口参数解析错误

gimbal/move接口的direction参数未做范围校验，导致越界值传入协议层。
修正：增加speed 1-10的范围检查。
```

**类型说明**:
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档变更
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具变更

---

## 分支策略

```
main          ← 生产分支，保持稳定
develop       ← 开发分支（如有需要）
feature/*     ← 功能分支
hotfix/*      ← 紧急修复分支
```

**分支命名**: `feature/xxx`、`hotfix/xxx`

---

## 提交流程

1. **创建分支**: `git checkout -b feature/your-feature`
2. **编写代码**: 遵循代码规范
3. **运行测试**: `pytest backend/tests/ -q` 确保全部通过
4. **提交变更**: `git commit -m "feat: xxx"`
5. **推送分支**: `git push origin feature/xxx`
6. **创建PR**: 在 GitHub 提交 Pull Request

---

## 文档贡献

### 文档目录

```
docs/
├── 官方文档/        ← 官方手册（只读引用）
│   ├── 机器狗本体/
│   └── 上装设备/
└── 项目文档/        ← 本项目文档（可编辑）
    ├── 01-需求分析.md
    ├── 02-项目架构.md
    ├── 03-模块说明.md
    ├── 04-机器狗环境说明.md
    ├── 05-部署说明.md
    ├── 06-演示方案.md
    └── 07-API参考.md
```

### 文档规范

- 使用 Markdown 格式
- 表头使用标准格式：`| 列1 | 列2 |`，分隔行使用 `|---|---|`
- 代码块标注语言：` ```bash `、` ```python `
- API路径与代码保持一致
- 机型名称统一使用"山猫 M20 Pro"

---

## 测试规范

### 运行测试

```bash
# 全量测试
PYTHONPATH=. uv run --with pytest pytest backend/tests/ -q

# 指定测试文件
PYTHONPATH=. uv run --with pytest pytest backend/tests/test_auth.py -v

# 覆盖率报告
PYTHONPATH=. uv run --with pytest coverage backend/tests/
```

### 新增测试

- 测试文件命名：`test_<模块名>.py`
- 测试函数命名：`test_<功能描述>`
- 断言使用 `assert` 语句

---

## 问题反馈

- **Bug报告**: 说明复现步骤、预期行为、实际行为
- **功能请求**: 说明使用场景、期望效果
- **文档问题**: 指出具体位置、建议修改内容

---

## 致谢

感谢所有为项目做出贡献的开发者！

---

**文档版本**: V1.0  
**最后更新**: 2026-08-16
