# 部署流程

## GOS 部署步骤

### 1. 登录 GOS

```bash
ssh user@10.21.31.104
```

### 2. 传输文件

使用 MobaXterm 文件浏览器，将 `m20-patrol-robot-deploy.tar.gz` 复制到 GOS：

```
本地路径: /path/to/m20-patrol-robot-deploy.tar.gz
远程路径: /tmp/m20-patrol-robot-deploy.tar.gz
```

### 3. 解压并进入目录

```bash
# 解压到 ~ 目录
mkdir -p ~/m20-patrol-robot
cd ~/m20-patrol-robot
tar xzf /tmp/m20-patrol-robot-deploy.tar.gz --strip-components=1
```

### 4. 执行部署（无需手动配置密码）

```bash
bash deploy/scripts/deploy-readonly.sh --one-shot
```

**首次部署自动完成**:
- 生成默认密码并保存到 `~/.config/m20-patrol/passwords.env`
- 创建 systemd 服务
- 启动服务

**预期输出**:
```
=== 预检 ===
检查Python环境...
Python: Python 3.8.10
Python环境检查通过 ✅
警告: 未找到密码文件，自动生成默认密码...
密码已保存到: /home/user/.config/m20-patrol/passwords.env
M20_GIMBAL_PASSWORD=m20_gimbal_xxxxxxxx
M20_ADMIN_PASSWORD=m20_admin_xxxxxxxx
...
预检通过 ✅

=== 安装服务 ===
复制文件到 /home/user/m20-patrol-robot...
编译Python代码...
准备systemd服务文件...
重新加载systemd...
安装完成 ✅

=== 启动服务 ===
服务启动请求已发送 ✅
```

### 5. 查看密码

```bash
bash deploy/scripts/deploy-readonly.sh --show-passwords
```

输出:
```
M20_GIMBAL_PASSWORD=m20_gimbal_xxxxxxxx
M20_ADMIN_PASSWORD=m20_admin_xxxxxxxx
```

### 6. 验证服务

```bash
# 检查服务状态
systemctl --user status m20-patrol-readonly

# 查看启动日志
journalctl --user -u m20-patrol-readonly -n 50 --no-pager
```

预期日志:
```
● m20-patrol-readonly.service - M20 Patrol Robot read-only dashboard
   Loaded: loaded (/home/user/.config/systemd/user/m20-patrol-readonly.service)
   Active: active (running) since ...
 Main PID: ... (python3)
    Tasks: ...
   CGroup: /user.slice/user-1000.slice/user@1000.service/...
           └─... python3 -m backend.app.server --manifest ...

INFO: M20 patrol robot starting (mode=realtime_readonly)
INFO: Connected to AOS at 10.21.31.103:30001
INFO: Health endpoint: http://10.21.31.104:8080/api/v1/health
```

### 7. 健康检查

```bash
curl http://127.0.0.1:8080/api/v1/health
```

预期输出:
```json
{
  "source": "REAL",
  "connected": true,
  "valid_frames": 123,
  "age_ms": 45
}
```

### 8. 本地访问

```bash
# 在本地笔记本执行（Windows 用 Git Bash 或 WSL）
ssh -L 8080:localhost:8080 user@10.21.31.104

# 浏览器访问
# http://localhost:8080/
# 用户名: admin
# 密码: m20_admin_xxxxxxxx（首次部署自动生成）
```

## 故障排查

### 服务未启动

```bash
systemctl --user status m20-patrol-readonly
journalctl --user -u m20-patrol-readonly -f
```

### 端口冲突

```bash
netstat -tlnp | grep 8080
systemctl --user stop m20-patrol-readonly
```

### 遥测无数据

```bash
curl http://127.0.0.1:8080/api/v1/status/latest
```

通过条件:
```
source=REAL, connected=true, valid_frames>0, age_ms < 3000
```

HTTP 200 不能替代真实遥测。

## 回滚部署

```bash
bash deploy/scripts/deploy-readonly.sh --stop
rm -rf ~/m20-patrol-robot
systemctl --user disable m20-patrol-readonly
systemctl --user daemon-reload
```
