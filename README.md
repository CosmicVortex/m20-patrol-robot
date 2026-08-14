# M20 Pro 巡逻机器人系统

面向中升之星奔驰的机器狗安保巡逻系统，基于山猫 M20 Pro 机器狗二次开发。

[![Version](https://img.shields.io/badge/version-V1.1.3-blue.svg)](./CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-232%20passed-green.svg)](./backend/tests/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](./LICENSE)

**机型**: 山猫 M20 Pro  
**部署位置**: GOS 主机（10.21.31.104）  
**通信协议**: basic_server（TCP 30001）  
**官方文档**: [山猫M20软件开发指南V1.2.1](./docs/官方文档/机器狗本体/山猫M20软件开发指南V1.2.1.md)

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
密码: 见部署配置文件（默认123456）
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
- **导航控制**：单点导航、任务管理
- **云台控制**：方向调节、变倍
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
| FFmpeg | 7.1+（支持 RTSP over TCP） |

### 网络要求

GOS主机需访问以下地址：

| 服务 | 地址 | 端口 | 用途 |
|------|------|------|------|
| AOS | 10.21.31.103 | 30001 | basic_server通信 |
| NOS | 10.21.31.106 | - | 导航服务 |
| 云台 | 10.21.31.108 | 80/554 | HTTP控制+RTSP视频 |

---

## 目录结构

```
m20-patrol-robot/
├── backend/                    # Python后端
│   ├── app/
│   │   ├── server.py           # 服务入口
│   │   ├── config.py           # 配置加载
│   │   ├── protocol/           # APDU帧编解码
│   │   ├── robot/              # basic_server客户端
│   │   ├── api/                # HTTP API处理器
│   │   ├── auth/               # 认证模块
│   │   ├── motion/             # 运动控制
│   │   ├── navigation/         # 导航控制
│   │   ├── gimbal/             # 云台控制
│   │   └── video/              # 视频管理
│   └── tests/                  # 单元测试 (232 cases)
├── deploy/                     # 部署脚本
│   ├── readonly-manifest.json  # 运行时配置
│   ├── scripts/                # 部署脚本
│   └── offline/ffmpeg/         # FFmpeg离线包
├── docs/
│   ├── 官方文档/
│   │   ├── 机器狗本体/         # 山猫协议文档 (16个)
│   │   └── 上装设备/           # 数尔云台文档 (4个)
│   └── 项目文档/
│       ├── 01-需求分析.md      # 功能需求、验收标准
│       ├── 02-项目架构.md      # 系统架构、模块划分
│       ├── 03-模块说明.md      # API接口完整列表
│       ├── 04-机器狗环境说明.md # 网络拓扑、诊断命令
│       ├── 05-部署说明.md      # 离线部署流程
│       └── 06-演示方案.md      # 演示流程设计
└── website/                    # Web前端
```

---

## API接口概览

| 类别 | 端点数 | 说明 |
|------|--------|------|
| 认证 | 3 | login/logout/me |
| 状态 | 3 | health/status/latest/devices |
| 运动控制 | 9 | state/gait/axis/light/charge/sleep/authorize/deauthorize/stop |
| 导航控制 | 5 | authorize/deauthorize/tasks/cancel/status |
| 云台控制 | 8 | connect/state/move/zoom/angle/scan/device-info/video |
| 视频管理 | 6 | status/config/probe/start/stop/playback |
| 业务管理 | 8 | work-orders/inspection-points/timeline/users/info |

完整API文档见 [03-模块说明.md](./docs/项目文档/03-模块说明.md)

---

## 故障排查

### 服务无法启动
```bash
journalctl --user -u m20-patrol-readonly -n 50
ss -tlnp | grep 8080
```

### 无法连接AOS
```bash
ping 10.21.31.103
nc -zv 10.21.31.103 30001
```

### FFmpeg问题
```bash
ffmpeg -version
ffprobe rtsp://10.21.31.103:8554/video1
```

---

## 开发说明

### 运行测试
```bash
cd /opt/data/m20-patrol-robot
PYTHONPATH=. uv run --with pytest pytest -q backend/tests/
```

### 编译检查
```bash
python3 -m compileall -q backend/
```

### 本地预览
```bash
cd docs/website
python3 -m http.server 8765
# 访问 http://localhost:8765/index.html
```

---

## 版本历史

详见 [CHANGELOG.md](./CHANGELOG.md)

---

## 许可证

MIT License - 详见 [LICENSE](./LICENSE)
