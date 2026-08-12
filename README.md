# M20 Pro 巡逻机器人二次开发

面向奔驰4S店的机器狗安保巡逻系统，基于山猫 M20 Pro 机器狗进行二次开发。

**演示机型**: M20 Pro  
**交付机型**: 山猫 M20 Pro
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
# 运行测试
PYTHONPATH=. uv run --with pytest pytest -q
```

### 3. GOS 部署

```bash
# 部署包必须使用 git archive --prefix=m20-patrol-robot/ 生成；
# 传输路径和登录用户由现场负责人确认。

# 在 GOS 上解压并部署
ssh user@10.21.31.104
tar xzf m20-patrol-robot-offline-deploy.tar.gz -C ~/
cd ~/m20-patrol-robot
bash deploy/scripts/deploy-readonly.sh --one-shot
```

### 4. 访问 Web 界面

现场验证通过后访问: `http://10.21.31.104:8080/`

登录账号：使用现场受控凭证；不要在文档、日志或聊天中记录密码。

---

## 核心功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 状态监控 | offline_verified | 状态解析和订阅逻辑通过离线测试；现场数据待复核 |
| 视频回传 | unverified | RTSP 地址与播放链路需现场验证 |
| 导航控制 | implemented | 报文构造已通过离线测试；控制链路已打通（控制模式）；需 Web 授权后执行 |
| 运动控制 | implemented | 服务已创建共享 client；控制端口已启用 transmit_enabled；需 Web 授权后执行 |
| 云台控制 | implemented | 适配器和 API 已实现；实物验证待完成 |
| 异常告警 | offline_verified | 错误码解析通过离线测试 |
| WebSocket | implemented | 服务端处理器已接线；浏览器端到端验证待完成 |

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
- **前端**: 原生 HTML/CSS/JavaScript（无框架）
- **通信**: TCP 30001（basic_server）、HTTP 8080（Web API）、WebSocket
- **认证**: SQLite + Session Cookie
- **测试**: pytest（可选依赖，开发环境使用）
- **视频**: ffmpeg（可选依赖，用于 RTSP 转码；离线部署时需通过 MobaXterm 传输安装）

### 离线安装 FFmpeg

GOS 目标架构为 `aarch64/arm64`。禁止将云端 `amd64`/`x86_64` 二进制复制到 GOS，禁止在线下载或手工覆盖系统目录。使用仓库内已校验的离线包和安装说明：

```bash
sha256sum -c deploy/offline/ffmpeg/SHA256SUMS
cd deploy/offline/ffmpeg
chmod +x install-ffmpeg-offline.sh
./install-ffmpeg-offline.sh
```

完整流程见 [`OFFLINE_FFMPEG_INSTALL.md`](./deploy/offline/ffmpeg/OFFLINE_FFMPEG_INSTALL.md)。

---

## 文档导航

| 文档 | 内容 | 读者 |
|------|------|------|
| [需求分析](./docs/项目文档/需求分析.md) | 功能清单、接口定义、验收规则 | PM、测试 |
| [项目架构](./docs/项目文档/项目架构.md) | 系统拓扑、协议端口、安全边界 | 架构师、开发 |
| [模块说明](./docs/项目文档/模块说明.md) | 代码结构、接口定义、测试覆盖 | 开发 |
| [机器狗环境说明](./docs/项目文档/机器狗环境说明.md) | 主机架构、环境配置、常用操作 | 运维、实施 |
| [部署说明](./docs/项目文档/部署说明.md) | 安装步骤、故障排查、回滚方案 | 运维 |
| [演示方案](./docs/项目文档/演示方案.md) | 演示流程、安全前置条件、应急预案 | 实施、项目管理 |
## 安全说明

1. **控制权限默认关闭** - 导航/运动控制需通过 Web UI 授权后启用（`control_enabled=true`）
2. **密码安全** - 凭证由受限环境文件提供；禁止在文档、日志或部署包中记录明文
3. **审计日志** - 所有控制操作记录到进程内存（最多 100 条）和 `journalctl`
4. **模拟标识** - 离线模式使用 `SIMULATED` 标识，不得显示为真实
5. **Web 授权强制** - 控制命令只能通过 Web UI 触发，底层 API 受门禁保护

---

## 许可证

内部项目，仅供演示与测试使用。

---

**版本**: V1.0.0  
**更新日期**: 2026-08-11  
**开发团队**: 云深处机器狗巡检二次开发
