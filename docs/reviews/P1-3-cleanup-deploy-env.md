# P1-3: 清理部署脚本无效环境变量

**问题**: 部署脚本设置但未使用的环境变量

**文件**: `deploy/scripts/deploy-readonly.sh`

**修改前**:
```bash
Environment=M20_TARGET_HOST=${AOS_HOST}
Environment=M20_TARGET_PORT=${AOS_TCP_PORT}
```

**修改后**: 删除这两行

**原因**: 应用从manifest读取AOS配置，不读取这些环境变量。

**验证**:
```bash
grep "M20_TARGET" deploy/scripts/deploy-readonly.sh
# 应无输出
```
