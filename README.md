# M20 Pro 巡逻机器人二次开发

面向奔驰4S店的机器狗安保巡逻系统，基于山猫 M20 Pro 机器狗进行二次开发。

**演示机型**: M20 Pro  
**交付机型**: 山猫 S10  
**部署位置**: GOS 主机（10.21.31.104）  
**通信协议**: basic_server（TCP 30001）  
**官方文档依据**: 山猫M20软件开发指南V1.2.1

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/CosmicVortex/m20-patrol-robot.git
cd m20-patrol-robot
```

### 2. 离线测试

```bash
# 安装依赖
uv sync

# 运行测试
uv run --with pytest python3 -m pytest backend/tests/ -q
```

### 3. GOS 部署

```bash
# 生成部署包
bash deploy/scripts/generate-deploy.sh

# 传输到 GOS
scp m20-patrol-robot-deploy.tar.gz user@10.21.31.104:/home/user/

# 在 GOS 上解压并部署
ssh user@10.21.31.104
tar xzf m20-patrol-robot-deploy.tar.gz -C ~/
cd ~/m20-patrol-robot
bash deploy/scripts/deploy-readonly.sh --one-shot
```

### 4. 访问 Web 界面

浏览器访问: `http://10.21.31.104:8080/`

登录账号: `admin` / `123456`

---

## 核心功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 状态监控 | ✅ | 实时订阅 AOS 状态消息（1002/4,5,6） |
| 视频回传 | 🟡 | RTSP 视频流管理（需现场验证地址） |
| 导航控制 | ✅ | 单点导航（Type=1003 Cmd=1），需授权 |
| 云台控制 | ✅ | 数尔云台 WEB 2.0 协议控制 |
| 异常告警 | ✅ | 解析错误码并展示 |
| WebSocket | ✅ | 实时数据推送 |

---

## 项目结构

```
m20-patrol-robot/
├── backend/                 # Python 后端服务
│   ├── app/
│   │   ├── protocol/       # APDU/ASDU 编解码
│   │   ├── robot/          # TCP 客户端、遥测适配器
│   │   ├── navigation/     # 导航报文构造、安全门控
│   │   ├── gimbal/         # 云台控制适配器
│   │   ├── video/          # 视频流管理
│   │   ├── auth/           # 认证鉴权
│   │   ├── api/            # HTTP API 处理器
│   │   ├── websocket/      # WebSocket 处理器
│   │   └── server.py       # 服务入口
│   └── tests/              # 单元测试
├── docs/
│   ├── 官方文档/           # 山猫官方手册、接口文档
│   │   ├── 机器狗本体/     # 山猫M20系列官方手册
│   │   └── 上装设备/       # 数尔云台资料
│   ├── 项目文档/           # 项目开发文档
│   │   ├── 需求分析.md
│   │   ├── 项目架构.md
│   │   ├── 模块说明.md
│   │   ├── 机器狗环境说明.md
│   │   ├── 部署说明.md
│   │   └── 演示方案.md
│   └── website/            # Web 前端静态资源
├── deploy/                  # 部署脚本与配置
│   ├── scripts/
│   ├── readonly-manifest.json
│   └── systemd/
└── README.md
```

---

## 技术栈

- **后端**: Python 3.8+（标准库，无额外依赖）
- **前端**: 原生 HTML/CSS/JavaScript
- **通信**: TCP 30001（basic_server）、HTTP 8080（Web API）、WebSocket
- **认证**: SQLite + Session Cookie
- **测试**: pytest

---

## 文档导航

| 文档 | 内容 | 读者 |
|------|------|------|
| [需求分析](./docs/项目文档/需求分析.md) | 功能清单、接口定义、验收规则 | PM、测试 |
| [项目架构](./docs/项目文档/项目架构.md) | 系统拓扑、协议端口、安全边界 | 架构师、开发 |
| [模块说明](./docs/项目文档/模块说明.md) | 代码结构、接口定义、测试覆盖 | 开发 |
| [机器狗环境说明](./docs/项目文档/机器狗环境说明.md) | 主机架构、环境配置、常用操作 | 运维、实施 |
| [部署说明](./docs/项目文档/部署说明.md) | 安装步骤、故障排查、回滚方案 | 运维 |
| [演示方案](./docs/项目文档/演示方案.md) | 演示流程、脚本、应急预案 | 销售、实施 |

---

## 安全说明

1. **控制权限默认关闭** - 导航/运动控制需书面放行后启用
2. **密码安全** - 默认密码 `123456`，生产环境需修改
3. **审计日志** - 所有控制操作记录到 `journalctl`
4. **模拟标识** - 离线模式使用 `SIMULATED` 标识，不得显示为真实

---

## 许可证

内部项目，仅供演示与测试使用。

---

**版本**: V1.0.0  
**更新日期**: 2026-08-11  
**开发团队**: 云深处机器狗巡检二次开发
