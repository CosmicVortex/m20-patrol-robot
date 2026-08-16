# M20 Pro 巡逻机器人系统

面向中升之星奔驰4S店的机器狗安保巡逻系统，基于山猫 M20 Pro 机器狗二次开发。

[![Version](https://img.shields.io/badge/version-V1.1.5-blue.svg)](./CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-232%20passed-green.svg)](./backend/tests/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](./LICENSE)

**机型**: 山猫 M20 Pro  
**部署位置**: GOS 主机（10.21.31.104）  
**状态**: 待实机验证  

---

## 快速开始

### 本地开发调试

```bash
cd /opt/data/m20-patrol-robot
./start.sh
```

### 生产部署

```bash
# 在GOS主机上执行
bash deploy/scripts/deploy-readonly.sh --one-shot
```

### 访问服务

```bash
# 健康检查
curl http://127.0.0.1:8080/api/v1/health

# 查看状态
curl http://127.0.0.1:8080/api/v1/status/latest
```

---

## 配置说明

### 生产模式

当前配置文件 `deploy/readonly-manifest.json` 设置为只读模式：

| 配置项 | 值 | 说明 |
|--------|-----|------|
| runtime_mode | realtime | 实时控制模式 |
| read_only_mode | false | 允许写操作 |
| control_enabled | true | 启用运动/导航控制 |
| telemetry_tx_enabled | true | 发送心跳 |
| allow_real_io | true | 允许真实IO |
| auth_enabled | false | 禁用认证（开发测试模式） |
| allow_anonymous | true | 允许匿名访问 |

### 本地测试模式

如需启用控制功能进行测试，修改配置文件：

```bash
# 编辑manifest
vim deploy/readonly-manifest.json

# 修改为测试模式
sed -i 's/"read_only_mode": true/"read_only_mode": false/' deploy/readonly-manifest.json
sed -i 's/"control_enabled": false/"control_enabled": true/' deploy/readonly-manifest.json
# 注：telemetry_tx_enabled和allow_real_io当前已为true，无需修改
```

---

## 端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 8080 | Web服务 | HTTP API + 静态文件（固定） |
| 30001 | AOS TCP | 遥测数据连接 |
| 8554 | RTSP | 视频流 |
| 80 | 云台HTTP | 云台控制API |

---

## 故障排查

### 端口被占用

```bash
# 查看占用
ss -tlnp | grep 8080

# 杀掉进程
sudo kill -9 <PID>

# 或修改配置文件中的端口
```

### 数据库锁定

```bash
# 删除旧数据库
rm -f backend/app/data/m20_auth.db

# 重新启动
./start.sh
```

---

## 文档索引

| 编号 | 文档 | 说明 |
|------|------|------|
| 01 | [项目概述与需求](./docs/项目文档/01-项目概述与需求.md) | 项目背景、目标、功能需求与验收标准 |
| 02 | [系统架构设计](./docs/项目文档/02-系统架构设计.md) | 系统架构、组件关系与技术栈 |
| 03 | [核心模块与协议](./docs/项目文档/03-核心模块与协议.md) | 核心模块职责、APDU协议与API端点 |
| 04 | [网络环境与部署拓扑](./docs/项目文档/04-网络环境与部署拓扑.md) | 网络拓扑、协议要点与诊断命令 |
| 05 | [部署指南与故障排查](./docs/项目文档/05-部署指南与故障排查.md) | 离线部署流程、配置管理与FAQ |
| 06 | [功能演示方案](./docs/项目文档/06-功能演示方案.md) | 功能演示流程与测试用例 |
| 07 | [API参考](./docs/项目文档/07-API参考.md) | 完整HTTP API接口文档 |
| 08 | [开发环境说明](./docs/项目文档/08-开发环境说明.md) | 本地开发调试指南 |

## 官方文档

| 文档 | 说明 |
|------|------|
| [山猫M20软件开发指南V1.2.1](./docs/官方文档/机器狗本体/山猫M20软件开发指南V1.2.1.md) | 官方协议与接口规范 |
| [山猫M20basic_server通信协议总览](./docs/官方文档/机器狗本体/山猫M20basic_server通信协议总览.md) | APDU消息格式详解 |
| [数尔WEB通讯协议V1.0](./docs/官方文档/上装设备/数尔WEB通讯协议V1.0.md) | 云台控制协议 |
| [数尔SR-UPA810T609规格文档](./docs/官方文档/上装设备/数尔SR-UPA810T609规格文档.md) | 云台硬件规格 |

## 其他文档

| 文档 | 说明 |
|------|------|
| [CHANGELOG](./CHANGELOG.md) | 版本历史与变更记录 |
| [CONTRIBUTING](./CONTRIBUTING.md) | 贡献指南 |
| [LICENSE](./LICENSE) | MIT 开源许可证 |

---

**部署文档**: [05-部署指南与故障排查.md](./docs/项目文档/05-部署指南与故障排查.md)
