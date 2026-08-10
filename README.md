# M20 Pro 巡逻机器人二次开发

M20 Pro 巡逻安防系统二次开发，部署于 GOS 主机，通过 basic_server 协议与 AOS 通信。

## 快速开始

### 部署（GOS 本机）

```bash
# 1. 解压部署包
tar xzf m20-patrol-robot-deploy.tar.gz -C ~/

# 2. 进入项目目录
cd ~/m20-patrol-robot

# 3. 执行部署
bash deploy/scripts/deploy-readonly.sh --one-shot
```

### 验证

```bash
# 检查服务状态
systemctl --user status m20-patrol-readonly

# 查看启动日志
journalctl --user -u m20-patrol-readonly -n 50 --no-pager

# 健康检查
curl http://127.0.0.1:8080/api/v1/health
```

### 访问 Web 界面

```bash
# 方式1：SSH 端口转发（本地笔记本）
ssh -L 8080:localhost:8080 user@10.21.31.104
# 浏览器访问: http://localhost:8080/

# 方式2：内网直接访问
# http://10.21.31.104:8080/

# 登录凭证
# 用户名: admin
# 密码: 123456（首次部署自动生成，见 ~/.config/m20-patrol/passwords.env）
```

## 系统架构

```
浏览器 → GOS (10.21.31.104:8080) → TCP 30001 → AOS (10.21.31.103) basic_server
                                   → RTSP 8554 → 本体相机
```

## 目标主机

| 主机 | IP | 角色 |
|------|-----|------|
| GOS | 10.21.31.104 | Web服务、二次开发 |
| AOS | 10.21.31.103 | 运动控制、basic_server |
| NOS | 10.21.31.106 | 建图、定位、导航 |

## 安全状态

- 只读模式：已启用
- 控制命令：已禁用
- 视频流：默认关闭（需配置实测地址）
- 导航授权：需现场书面确认

## 文档

- [项目概览](docs/项目文档/01-overview.md)
- [系统架构](docs/项目文档/02-architecture.md)
- [部署流程](docs/项目文档/06-deployment.md)
- [测试流程](docs/项目文档/05-testing.md)

## 状态

- 155 测试通过
- 云端离线基线完成
- GOS现场部署成功（2026-08-11）
- 等待书面放行后启用控制功能
