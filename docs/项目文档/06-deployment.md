# 部署流程

## 环境要求

**GOS主机**:
- 系统: Ubuntu 20.04.6 LTS (aarch64)
- Python: 3.8.10（系统预装）
- 磁盘空间: ≥50MB
- 网络: 可访问 AOS (10.21.31.103:30001)

## 部署步骤

### 步骤1：传输部署包到GOS

```bash
# 方式1：scp传输
scp m20-patrol-robot-deploy.tar.gz user@10.21.31.104:/home/user/

# 方式2：MobaXterm 文件浏览器拖拽上传
```

### 步骤2：SSH登录GOS并解压

```bash
ssh user@10.21.31.104

# 解压部署包（自动创建 ~/m20-patrol-robot/ 目录）
tar xzf m20-patrol-robot-deploy.tar.gz -C ~/
cd ~/m20-patrol-robot
```

### 步骤3：预检

```bash
bash deploy/scripts/deploy-readonly.sh --preflight
```

**预期输出**:
```
=== 预检 ===
检查Python环境...
Python: Python 3.8.10
Python环境检查通过 ✅

GIMBAL_PASSWORD=123456
ADMIN_PASSWORD=123456

目标目录: /home/user/m20-patrol-robot
配置: 已加载
GOS_HOST=10.21.31.104
AOS_HOST=10.21.31.103
NOS_HOST=10.21.31.106
WEB_PORT=8080
AOS_TCP_PORT=30001

预检完成 ✅
```

### 步骤4：执行部署

```bash
bash deploy/scripts/deploy-readonly.sh --one-shot
```

**预期输出**:
```
=== 安装服务 ===
复制文件到 /home/user/m20-patrol-robot...
已在目标目录，跳过复制
编译Python代码...
准备systemd服务文件...
重新加载systemd...

安装完成 ✅

配置信息:
  服务: m20-patrol-readonly.service
  地址: http://10.21.31.104:8080
  用户名: admin
  密码: 123456
  密码文件: /home/user/.config/m20-patrol/passwords.env

=== 启动服务 ===
服务启动请求已发送 ✅

=== 服务状态 ===
● m20-patrol-readonly.service - M20 Patrol Robot read-only dashboard
   Active: active (running)
```

### 步骤5：验证服务

```bash
# 检查服务状态
systemctl --user status m20-patrol-readonly

# 查看启动日志
journalctl --user -u m20-patrol-readonly -n 50 --no-pager

# 健康检查API
curl http://127.0.0.1:8080/api/v1/health

# 状态查询
curl http://127.0.0.1:8080/api/v1/status/latest
```

**健康检查预期输出**:
```json
{
  "service": "m20-patrol-web",
  "runtime_mode": "realtime_readonly",
  "read_only_mode": true,
  "connected": false,
  "source": "NO_DATA",
  "healthy": false
}
```

> **注意**: `connected=false` 和 `source=NO_DATA` 是正常的，表示遥测连接尚未建立。当AOS服务正常运行时，这些字段会变为 `connected=true` 和 `source=REAL`。

### 步骤6：访问Web界面

```bash
# 方式1：本地SSH端口转发
ssh -L 8080:localhost:8080 user@10.21.31.104
# 浏览器访问: http://localhost:8080/

# 方式2：内网直接访问
# 浏览器: http://10.21.31.104:8080/
```

**登录凭证**:
- 用户名: `admin`
- 密码: `123456`（首次部署自动生成，保存于 `~/.config/m20-patrol/passwords.env`）

## 故障排查

### 服务未启动

```bash
# 查看服务状态
systemctl --user status m20-patrol-readonly

# 查看详细日志
journalctl --user -u m20-patrol-readonly -n 100 --no-pager

# 手动测试服务
cd ~/m20-patrol-robot
PYTHONPATH=. python3 -m backend.app.server --manifest deploy/readonly-manifest.json --verbose
```

### 端口被占用

```bash
# 检查端口占用
netstat -tlnp | grep 8080

# 停止占用进程
sudo kill <PID>

# 服务会自动尝试备用端口（8081-8090）
```

### AOS连接失败

```bash
# 测试连接
timeout 3 bash -c 'echo > /dev/tcp/10.21.31.103/30001' && echo "连接成功" || echo "连接失败"
```

## 回滚部署

```bash
# 停止并删除服务
bash deploy/scripts/deploy-readonly.sh --stop

# 清理部署目录
rm -rf ~/m20-patrol-robot
```

## 安全说明

1. **控制权限默认关闭**
   - `read_only_mode=true`
   - `control_enabled=false`
   - 导航控制需书面放行

2. **密码安全**
   - 密码文件路径: `~/.config/m20-patrol/passwords.env`
   - 权限: `600`
   - 禁止提交密码到Git仓库

3. **审计日志**
   - 所有操作记录到 `journalctl`
   - 日志保留30天
