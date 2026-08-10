# 部署流程

## GOS 部署步骤

### 1. 登录 GOS

```bash
ssh user@10.21.31.104
# 密码：your_gos_password
```

### 2. 传输文件

使用 MobaXterm 文件浏览器，将 `m20-patrol-code.zip` 复制到 GOS：

```
本地路径: /path/to/m20-patrol-code.zip
远程路径: /home/user/m20-patrol-code.zip
```

### 3. 解压并进入目录

```bash
unzip m20-patrol-code.zip -d ~/.local/share/m20-patrol-robot
cd ~/.local/share/m20-patrol-robot
```

### 4. 设置密码

首次部署需创建密码文件：

```bash
mkdir -p ~/.config/m20-patrol
cat > ~/.config/m20-patrol/passwords.env <<EOF
export M20_GIMBAL_PASSWORD='your_gimbal_password'
export M20_ADMIN_PASSWORD='your_admin_password'
EOF
chmod 600 ~/.config/m20-patrol/passwords.env
```

### 5. 预检查

```bash
bash deploy/scripts/deploy-readonly.sh --preflight
```

预期输出：
```
检查Python环境...
Python: Python 3.8.10
Python环境检查通过 ✅

GIMBAL_PASSWORD=***
ADMIN_PASSWORD=***

目标目录: /home/user/.local/share/m20-patrol-robot
服务名称: m20-patrol-readonly.service
Web端口: 8080
AOS地址: 10.21.31.103:30001
NOS地址: 10.21.31.106
控制模式: false
遥测发送: false
...
预检通过
```

### 6. 执行部署

```bash
bash deploy/scripts/deploy-readonly.sh --one-shot
```

预期输出：
```
=== 部署 M20 巡逻机器人 ===
目标目录: /home/user/.local/share/m20-patrol-robot
服务名称: m20-patrol-readonly.service
...
复制文件...
安装服务...
启用服务...
启动服务...
部署完成
```

### 7. 验证服务

```bash
# 检查服务状态
systemctl --user status m20-patrol-readonly

# 查看启动日志
journalctl --user -u m20-patrol-readonly -n 50 --no-pager
```

预期日志：
```
● m20-patrol-readonly.service - M20 Patrol Robot (readonly)
   Loaded: loaded (/home/user/.config/systemd/user/m20-patrol-readonly.service)
   Active: active (running) since ...
 Main PID: ... (python3)
    Tasks: ...
   CGroup: /user.slice/user-1000.slice/user@1000.service/...
           └─... python3 -m backend.app.server --manifest ...

...
INFO: M20 patrol robot starting (mode=realtime_readonly)
INFO: Connected to AOS at 10.21.31.103:30001
INFO: Health endpoint: http://10.21.31.104:8080/api/v1/health
```

### 8. 健康检查

```bash
curl http://127.0.0.1:8080/api/v1/health
```

预期输出：
```json
{
  "source": "REAL",
  "connected": true,
  "valid_frames": 123,
  "age_ms": 45
}
```

### 9. 本地访问

```bash
# 在本地笔记本执行（Windows 用 Git Bash 或 WSL）
ssh -L 8080:localhost:8080 user@10.21.31.104

# 浏览器访问
# http://localhost:8080/
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

通过条件：
```
source=REAL, connected=true, valid_frames>0, age_ms < 3000
```

HTTP 200 不能替代真实遥测。
