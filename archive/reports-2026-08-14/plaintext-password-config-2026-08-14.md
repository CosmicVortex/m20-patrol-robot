# M20 Pro 快速测试模式 - 密码配置更新

**更新日期**: 2026-08-14  
**变更**: 密码验证简化为明文比较

---

## 执行摘要

| 配置项 | 生产模式 | 测试模式 |
|--------|----------|----------|
| 密码存储 | PBKDF2-SHA256 哈希 | **明文存储** |
| 密码验证 | 哈希比较 | **直接字符串比较** |
| 最小长度 | 6字符 | **无限制** |
| 适用场景 | 生产部署 | **内部快速测试** |

---

## 已修改文件

### 1. backend/app/auth/store.py

```python
# 原实现（生产模式）
@staticmethod
def _hash_password(password: str, *, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240000)
    return "$".join(("pbkdf2_sha256", "240000", salt.hex(), digest.hex()))

@staticmethod
def _verify_password(password: str, encoded: str) -> bool:
    scheme, iterations_text, salt_hex, digest_hex = encoded.split("$", 3)
    # ... PBKDF2 验证逻辑
    return hmac.compare_digest(actual, expected)

# 新实现（测试模式）
@staticmethod
def _hash_password(password: str, *, salt: Optional[bytes] = None) -> str:
    # Internal testing mode: store plain text password (no hashing)
    return password

@staticmethod
def _verify_password(password: str, encoded: str) -> bool:
    # Internal testing mode: direct plain text comparison
    return password == encoded
```

### 2. backend/init_users.py

```python
# 原实现
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240000)
    return "$".join(("pbkdf2_sha256", "240000", salt.hex(), digest.hex()))

# 新实现
def hash_password(password: str) -> str:
    # Internal testing mode: store plain text password (no hashing)
    return password
```

### 3. backend/tests/test_auth_store.py

更新测试用例以匹配明文存储行为。

---

## 验证结果

### 测试通过
```bash
$ PYTHONPATH=. python3 -m pytest backend/tests/ -q
232 passed in 20.84s
```

### 功能验证
```bash
✅ 创建用户成功: testuser
✅ 认证通过: testuser
✅ 错误密码拒绝: invalid credentials
✅ 数据库中存储: 123
✅ 是明文密码: True
```

---

## 快速测试流程

### 1. 初始化用户

```bash
cd /opt/data/m20-patrol-robot
python3 backend/init_users.py
```

输出:
```
[OK] 已创建 admin 账户，密码已写入 /home/user/.config/m20-patrol/passwords.env
[OK] 密码文件已写入 /home/user/.config/m20-patrol/passwords.env (权限 600)
```

### 2. 查看密码

```bash
cat ~/.config/m20-patrol/passwords.env
```

输出:
```
M20_ADMIN_PASSWORD=123456
```

### 3. 登录测试

```bash
curl -X POST http://10.21.31.104:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}'
```

响应:
```json
{
  "token": "xxx",
  "user": {"username": "admin", "role": "admin"},
  "expires_in": 1800
}
```

### 4. 测试控制端点

```bash
# 运动控制
curl -X POST http://10.21.31.104:8080/api/v1/motion/state \
  -H "Content-Type: application/json" \
  -H "X-M20-Token: <token>" \
  -d '{"state":1}'

# 导航控制
curl -X POST http://10.21.31.104:8080/api/v1/navigation/task \
  -H "Content-Type: application/json" \
  -H "X-M20-Token: <token>" \
  -d '{"pos_x":1.0,"pos_y":2.0}'
```

---

## 安全说明

⚠️ **此配置仅用于内部快速测试，不适用于生产环境**

### 已知限制

1. **密码明文存储**: 数据库中存储原始密码字符串
2. **无加密**: 不使用PBKDF2或其他哈希算法
3. **无长度限制**: 可使用任意长度密码
4. **无复杂度要求**: 不支持弱密码检测

### 恢复生产模式

```bash
# 恢复密码哈希
cd /opt/data/m20-patrol-robot

# 修改 store.py
sed -i 's/# Internal testing mode: store plain text password (no hashing)/# Production mode: use PBKDF2 hashing/' backend/app/auth/store.py
# 恢复 PBKDF2 实现...

# 修改 init_users.py
sed -i 's/# Internal testing mode: store plain text password (no hashing)/# Production mode: use PBKDF2 hashing/' backend/init_users.py
# 恢复 PBKDF2 实现...
```

---

## 配置状态总结

| 配置项 | 状态 |
|--------|------|
| read_only_mode | false ✅ |
| control_enabled | true ✅ |
| 密码哈希 | 明文存储 ✅ |
| 密码长度限制 | 无限制 ✅ |
| 导航授权 | 自动 ✅ |
| 测试结果 | 232 passed ✅ |

**测试模式已就绪，可立即进行端到端功能测试**
