# M20 Pro 部署问题分析与解决方案

## 🔍 问题诊断总结

### 错误1: GOS身份检查失败
```
ERROR: GOS identity mismatch
```
**原因**: GOS主机上 `ip` 命令不在PATH中

### 错误2: Python版本不匹配（根本问题）
```
BLOCKED:PY38_RUNTIME_CHECK_BLOCKED
```
**原因**: 部署脚本强制要求 Python 3.8.10，但GOS主机只有 Python 3.13.5

---

## 📊 详细分析

### 1. GOS主机环境
| 项目 | 值 |
|------|-----|
| 操作系统 | Ubuntu 20.04.6 LTS (aarch64) |
| Python版本 | 3.13.5 |
| ip命令 | 不在PATH中 |
| GOS IP | 10.21.31.104 ✓ 已确认 |

### 2. 部署脚本检查逻辑

**deploy-readonly.sh 第80-82行**:
```bash
PYTHON_BIN="$(command -v python3.8 || true)"
[ -n "$PYTHON_BIN" ] || fail 'PY38_RUNTIME_CHECK_BLOCKED'
"$PYTHON_BIN" -c 'import sys; assert sys.version_info[:3] == (3,8,10)' || fail 'PY38_RUNTIME_CHECK_BLOCKED'
```
→ 查找 `python3.8` 命令，未找到则失败

**install-gos.sh 第249-251行**:
```bash
PYTHON38_BIN="$(command -v python3.8 || true)"
[ -n "$PYTHON38_BIN" ] || { printf 'ERROR: python3.8 is required...' >&2; exit 1; }
"$PYTHON38_BIN" -c 'import sys; assert sys.version_info[:3] == (3,8,10)' || ...
```
→ 同样要求 Python 3.8.10

---

## ✅ 解决方案

### 方案A: 在GOS主机安装Python 3.8.10（推荐）

```bash
# 方法1: 使用pyenv安装（推荐）
curl https://pyenv.run | bash
export PATH="$HOME/.pyenv/bin:$PATH"
pyenv install 3.8.10
pyenv global 3.8.10
python3 --version  # 确认输出 Python 3.8.10

# 方法2: 从源码编译
wget https://www.python.org/ftp/python/3.8.10/Python-3.8.10.tgz
tar -xzf Python-3.8.10.tgz
cd Python-3.8.10
./configure --enable-optimizations
make -j$(nproc)
make install
sudo ln -sf /usr/local/bin/python3.8 /usr/local/bin/python3.8.10
```

### 方案B: 修改部署脚本支持Python 3.13+

我将修改脚本，使其兼容Python 3.13：

<tool_call>
<function=read_file>