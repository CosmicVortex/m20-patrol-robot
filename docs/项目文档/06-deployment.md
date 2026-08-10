# 部署流程

## GOS 部署步骤

### 1. 登录 GOS

```bash
ssh user@10.21.31.104
```

### 2. 解压部署包

```bash
# 删除旧版本
rm -f ~/m20-patrol-robot-deploy.tar.gz
rm -rf ~/m20-patrol-robot

# 解压新版本
tar xzf m20-patrol-robot-deploy.tar.gz -C ~/
cd ~/m20-patrol-robot
```

### 3. 运行诊断（可选）

```bash
bash deploy/scripts/diagnose.sh
```

### 4. 执行部署

```bash
bash deploy/scripts/deploy-readonly.sh --one-shot
```

### 5. 验证服务

```bash
# 检查服务状态
systemctl --user status m20-patrol-readonly

# 查看日志
journalctl --user -u m20-patrol-readonly -f

# 测试健康检查
curl http://127.0.0.1:8080/api/v1/health

# 访问Web界面
# 浏览器: http://10.21.31.104:8080/
# 用户名: admin
# 密码: 123456（或首次部署生成的密码）
```

## 故障排查

### 服务启动后立即退出

```bash
# 查看详细日志
journalctl --user -u m20-patrol-readonly -n 100 --no-pager

# 手动测试
cd ~/m20-patrol-robot
PYTHONPATH=. python3 -m backend.app.server --manifest deploy/readonly-manifest.json --verbose
```

### 端口被占用

```bash
# 检查端口占用
netstat -tlnp | grep 8080

# 停止占用进程
sudo kill <PID>

# 或服务会自动使用备用端口(8081)
```

### AOS连接失败

```bash
# 测试连接
timeout 3 bash -c 'echo > /dev/tcp/10.21.31.103/30001' && echo "连接成功" || echo "连接失败"

# 检查防火墙
sudo iptables -L -n | grep 30001
```

## 回滚部署

```bash
bash deploy/scripts/deploy-readonly.sh --stop
rm -rf ~/m20-patrol-robot
```
