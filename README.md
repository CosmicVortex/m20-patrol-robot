# M20 Pro 巡逻机器人系统

面向中升之星奔驰的机器狗安保巡逻系统，基于山猫 M20 Pro 机器狗二次开发。

**机型**: 山猫 M20 Pro  
**部署位置**: GOS 主机（10.21.31.104）  
**通信协议**: basic_server（TCP 30001）  
**官方文档**: 山猫M20软件开发指南V1.2.1

---

## 快速开始

### 1. 部署到GOS主机

```bash
# 在本地构建部署包
bash deploy/scripts/build-offline-deploy-package.sh

# 传输到GOS主机
scp m20-patrol-robot.zip user@10.21.31.104:/home/user/

# SSH登录并部署
ssh user@10.21.31.104
unzip -q m20-patrol-robot.zip -d ~/m20-patrol-robot
cd ~/m20-patrol-robot
bash deploy/scripts/deploy-readonly.sh --one-shot
```

### 2. 访问Web界面

```bash
# 浏览器访问
http://10.21.31.104:8080/

# 登录账号
用户名: admin
密码: 123456（首次登录后请修改）
```

### 3. 验证服务状态

```bash
# 健康检查
curl http://127.0.0.1:8080/api/v1/health

# 查看服务日志
journalctl --user -u m20-patrol-readonly -f
```

---

## 项目特性

- **实时状态监控**：机器狗位置、电量、运动状态实时刷新
- **四路视频回传**：前/后广角+热成像+云台可见光
- **导航控制**：单点导航、任务管理、路径规划
- **云台控制**：方向调节、变倍、预置点
- **异常告警**：错误码解析、告警工单管理
- **离线部署**：无网络依赖，适合现场环境

---

## 环境要求

### GOS主机配置

| 项目 | 要求 |
|------|------|
| 系统 | Ubuntu 20.04.6 LTS (aarch64) |
| Python | 3.8.10（系统预装） |
| 磁盘 | ≥1GB可用空间 |
| 内存 | ≥4GB RAM |

### 网络要求

GOS主机需访问以下地址：

| 服务 | 地址 | 端口 | 用途 |
|------|------|------|------|
| AOS | 10.21.31.103 | 30001 | basic_server通信 |
| NOS | 10.21.31.106 | - | 导航服务 |
| 云台 | 10.21.31.108 | 80/554 | HTTP控制+RTSP视频 |

### FFmpeg依赖

视频播放需要 FFmpeg 7.1+，支持 RTSP over TCP。

```bash
# 验证安装
command -v ffmpeg && ffmpeg -version
```

---

## 目录结构

```
m20-patrol-robot/
├── backend/                    # Python后端
│   ├── app/
│   │   ├── server.py           # 服务入口
│   │   ├── config.py           # 配置加载
│   │   ├── protocol/           # APDU帧编解码
│   │   ├── robot/              # TCP客户端、遥测适配器
│   │   ├── navigation/         # 导航控制
│   │   ├── motion/             # 运动控制
│   │   ├── gimbal/             # 云台控制
│   │   ├── video/              # 视频流管理
│   │   ├── auth/               # 认证鉴权
│   │   ├── api/                # HTTP API
│   │   └── websocket/          # WebSocket支持
│   └── tests/                  # 单元测试
├── deploy/
│   ├── scripts/                # 部署脚本
│   ├── offline/ffmpeg/         # FFmpeg离线包
│   └── readonly-manifest.json  # 运行时配置
├── docs/
│   ├── 官方文档/               # 山猫官方手册
│   │   ├── 机器狗本体/         # 16份协议文档
│   │   └── 上装设备/           # 3份云台资料
│   ├── 项目文档/               # 项目文档
│   └── website/                # Web前端资源
└── README.md
```

---

## API端点

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/auth/login | 用户登录 |
| POST | /api/v1/auth/logout | 退出登录 |

### 状态查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/status/latest | 最新状态 |
| GET | /api/v1/status/history | 历史状态 |

### 导航控制

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/navigation/authorize | 授权导航 |
| POST | /api/v1/navigation/tasks | 创建任务 |
| POST | /api/v1/navigation/cancel | 取消任务 |

### 云台控制

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/gimbal/state | 云台状态 |
| POST | /api/v1/gimbal/move | 方向控制 |
| POST | /api/v1/gimbal/zoom | 变倍控制 |
| POST | /api/v1/gimbal/preset | 预置点 |

### 视频管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/video | 视频状态 |
| POST | /api/v1/video/config | 配置RTSP地址 |

---

## 故障排查

### 服务未启动

```bash
# 检查服务状态
systemctl --user status m20-patrol-readonly

# 查看启动日志
journalctl --user -u m20-patrol-readonly -n 50 --no-pager
```

### 端口被占用

```bash
# 检查端口
netstat -tlnp | grep :8080

# 服务会自动尝试备用端口（8081-8090）
```

### AOS连接失败

```bash
# 测试TCP连接
timeout 3 bash -c 'echo > /dev/tcp/10.21.31.103/30001' && echo "OK" || echo "FAIL"
```

---

## 官方文档

- [山猫M20软件开发指南V1.2.1](./docs/官方文档/机器狗本体/山猫M20软件开发指南V1.2.1.md)
- [basic_server通信协议](./docs/官方文档/机器狗本体/山猫M20basic_server通信协议总览.md)
- [数尔WEB通讯协议](./docs/官方文档/上装设备/数尔WEB通讯协议V1.0.md)

---

**版本**: V1.0.0  
**更新日期**: 2026-08-13  
**部署客户**: 中升之星奔驰