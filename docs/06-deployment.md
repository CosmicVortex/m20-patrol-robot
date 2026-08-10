# 部署流程

## GOS 部署

### 1. SSH 登录 GOS

```bash
ssh user@10.21.31.104
```

### 2. 解压并部署

```bash
# 将 m20-patrol-code.zip 上传到 GOS，然后解压
unzip m20-patrol-code.zip -d ~/.local/share/m20-patrol-robot
cd ~/.local/share/m20-patrol-robot
```

### 3. 预检查

```bash
bash deploy/scripts/deploy-readonly.sh --preflight
```

预期输出：
```
...
```

### 4. 执行部署

```bash
bash deploy/scripts/deploy-readonly.sh --one-shot
```

预期输出：
```
...
```

### 5. 验证服务

```bash
# 检查服务状态
systemctl --user status m20-patrol-readonly

# 查看启动日志
journalctl --user -u m20-patrol-readonly -n 50 --no-pager
```

预期日志：
```
...
```

### 6. 本地访问

```bash
# 在本地笔记本执行（Windows 用 Git Bash 或 WSL）
ssh -L 8080:localhost:8080 user@10.21.31.104

# 浏览器访问
# http://localhost:8080/
```

## 健康检查

```bash
curl http://127.0.0.1:8080/api/v1/health
```

通过条件：
```
source=REAL, connected=true, valid_frames>0
```

HTTP 200 不能替代真实遥测。

## 环境变量

首次部署需设置密码：

```bash
export M20_GIMBAL_PASSWORD='your_password'
export M20_ADMIN_PASSWORD='your_password'
```

密码保存位置：`~/.config/m20-patrol/passwords.env`

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
