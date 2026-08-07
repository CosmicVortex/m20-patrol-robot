# 06 — 部署流程

## 部署模式

| 模式 | 适用场景 | Python 版本 | 外部依赖 | 说明 |
|---|---|---|---|---|
| 简化版 | GOS Python 3.8、离线环境 | 3.8+ | 无 | 仅显示 SIMULATED 状态 |
| 完整版 | Python 3.11+、已连接 AOS | 3.11+ | 无 | 连接真实 AOS 状态订阅 |

---

## 快速部署（推荐）

### 方式一：从压缩包部署（离线）

```bash
# 1. 上传压缩包到 GOS
scp m20-patrol-deploy-v2.zip user@10.21.31.104:/home/user/

# 2. SSH 登录 GOS
ssh user@10.21.31.104

# 3. 解压并部署
cd ~
unzip -o m20-patrol-deploy-v2.zip

# 4. 执行部署脚本
./m20-patrol-deploy-v2.sh
```

### 方式二：从 Git 仓库部署

```bash
# 1. 克隆仓库（如已克隆则跳过）
cd ~
git clone /path/to/m20-patrol-robot.git
cd m20-patrol-robot

# 2. 切换到批准版本
git checkout <APPROVED_COMMIT_SHA>

# 3. 执行部署
bash deploy/scripts/start.sh
```

---

## 服务管理

### 启动服务

```bash
# 简化版（无外部依赖）
python3 backend/app/dashboard_simple.py &

# 完整版（连接真实 AOS）
python3 -c "
import sys
sys.path.insert(0, '.')
from backend.app.dashboard_realtime import serve_dashboard
serve_dashboard(host='127.0.0.1', port=8080, aos_host='10.21.31.103')
" &
```

### 验证服务

```bash
# 检查端口
ss -tlnp | grep 8080

# 测试 API
curl http://127.0.0.1:8080/api/v1/status/latest

# 健康检查
curl http://127.0.0.1:8080/api/v1/health
```

### 停止服务

```bash
pkill -f dashboard_simple
# 或
pkill -f dashboard_realtime
```

---

## 从笔记本访问

```powershell
# 端口转发
ssh -L 8080:127.0.0.1:8080 user@10.21.31.104

# 浏览器访问
http://localhost:8080/
```

---

## 验证清单

| 检查项 | 命令 | 预期结果 |
|---|---|---|
| 端口监听 | `ss -tlnp \| grep 8080` | 显示 `:8080` |
| API 响应 | `curl http://127.0.0.1:8080/api/v1/status/latest` | JSON 响应 |
| 健康检查 | `curl http://127.0.0.1:8080/api/v1/health` | `{"status": "ok"}` |
| 页面访问 | `curl http://127.0.0.1:8080/` | HTML 页面 |
| 状态标识 | `grep -E 'SIMULATED|REAL'` | 显示对应标识 |

---

## 故障排查

### 服务无法启动

```bash
# 查看日志
tail -50 /tmp/dashboard_simple.log
tail -50 /tmp/dashboard_realtime.log

# 检查端口占用
ss -tlnp | grep 8080

# 检查 Python 环境
python3 --version
```

### 无法连接 AOS

```bash
# 测试 TCP 连通性
nc -zv 10.21.31.103 30001

# 检查防火墙
sudo iptables -L -n | grep 30001
```

---

## 禁止操作

以下操作在未获得书面放行前禁止执行：

- ❌ 发送心跳以外的控制报文
- ❌ 发送 1003/1 导航下发命令
- ❌ 发送 1004/1 取消命令
- ❌ 发送运动控制命令（Type=2, Cmd=21/22/23/24/25）
- ❌ 修改 AOS/NOS 系统服务
- ❌ 复制地图到其他场地
