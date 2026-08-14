# M20 Pro 快速测试模式配置报告

**配置日期**: 2026-08-14  
**模式**: 内部快速测试（一键启动）

---

## 执行摘要

| 配置项 | 状态 |
|--------|------|
| 一键启动 | ✅ ./start.sh |
| read_only_mode | false |
| control_enabled | true |
| 密码存储 | 明文 |
| 导航授权 | 自动 |
| 测试结果 | 232 passed |

---

## 快速启动

### 方式一：一键启动（推荐）

```bash
cd /opt/data/m20-patrol-robot
./start.sh
```

### 方式二：直接运行

```bash
python3 backend/app/server.py
```

### 方式三：带参数启动

```bash
# 指定端口
python3 backend/app/server.py --port 9090

# 详细日志
python3 backend/app/server.py --verbose

# 自定义配置
python3 backend/app/server.py --manifest deploy/readonly-manifest.json
```

---

## 启动流程

服务启动时自动执行：

1. ✅ 加载配置文件（deploy/readonly-manifest.json）
2. ✅ 初始化用户数据库（admin/123456）
3. ✅ 创建认证中间件
4. ✅ 初始化遥测适配器
5. ✅ 初始化导航服务（自动授权）
6. ✅ 初始化运动控制服务
7. ✅ 绑定HTTP端口（默认8080）
8. ✅ 启动WebSocket处理器

**无需任何手动配置，开箱即用。**

---

## 测试验证

### 编译检查
```bash
python3 -m compileall -q backend/
```

### 单元测试
```bash
PYTHONPATH=. python3 -m pytest backend/tests/ -q
# 232 passed in 20.84s
```

### 端到端测试
```bash
# 启动服务
./start.sh &

# 健康检查
curl http://127.0.0.1:8080/api/v1/health

# 登录（任意密码）
curl -X POST http://127.0.0.1:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"any"}'

# 运动控制
curl -X POST http://127.0.0.1:8080/api/v1/motion/state \
  -H "Content-Type: application/json" \
  -d '{"state":1}'

# 导航控制
curl -X POST http://127.0.0.1:8080/api/v1/navigation/task \
  -H "Content-Type: application/json" \
  -d '{"pos_x":1.0,"pos_y":2.0}'
```

---

## 配置说明

### manifest.json

```json
{
  "read_only_mode": false,
  "control_enabled": true,
  "auth_enabled": false,
  "allow_anonymous": true,
  "allow_real_io": true
}
```

### 端口分配

| 服务 | 端口 | 说明 |
|------|------|------|
| Web服务 | 8080 | HTTP API + 静态文件 |
| AOS TCP | 30001 | 机器狗遥测数据 |
| AOS UDP | 30000 | 机器狗命令发送 |
| RTSP | 8554 | 视频流 |
| 云台HTTP | 80 | 云台控制API |

---

## 安全说明

⚠️ **此配置仅用于内部快速测试**

### 已知限制
- 密码明文存储
- 无密码长度限制
- 导航自动授权
- 认证可跳过

### 恢复生产模式
```bash
# 编辑 manifest.json
sed -i 's/"read_only_mode": false/"read_only_mode": true/' deploy/readonly-manifest.json
sed -i 's/"control_enabled": true/"control_enabled": false/' deploy/readonly-manifest.json
sed -i 's/"auth_enabled": false/"auth_enabled": true/' deploy/readonly-manifest.json
```

---

## 故障排查

### 端口被占用
```bash
# 查看端口占用
ss -tlnp | grep 8080

# 杀掉占用进程
sudo kill -9 <PID>

# 或使用备用端口
python3 backend/app/server.py --port 8081
```

### 数据库锁定
```bash
# 删除旧数据库（会重置admin账户）
rm -f backend/app/data/m20_auth.db

# 重新启动服务
./start.sh
```

### 云台连接失败
```bash
# 检查云台网络
ping 10.21.31.108
curl http://10.21.31.108/api/status

# 修改云台地址
sed -i 's/10.21.31.108/<new_ip>/' deploy/readonly-manifest.json
```

---

**测试模式已就绪，可立即进行端到端功能测试**
