# M20 Pro 巡逻机器人二次开发

山猫 M20 Pro 机器狗巡逻安防系统二次开发项目。通过 `basic_server` 协议与 AOS 通信，提供状态监控、视频回传和受控导航能力。

## 硬件配置

| 组件 | IP 地址 | 职责 | 访问方式 |
|------|---------|------|----------|
| GOS | 10.21.31.104 | 用户开发机、Web服务 | SSH/VNC 可访问 |
| AOS | 10.21.31.103 | 运动控制、basic_server | ❌ 不可直接访问 |
| NOS | 10.21.31.106 | 建图、定位、导航 | SSH/VNC 可访问 |

## 网络接口

| 服务 | 端口 | 用途 |
|------|------|------|
| basic_server TCP | 30001 | 状态订阅、任务下发 |
| basic_server UDP | 30000 | 高频速度指令（≥20Hz） |
| RTSP | 8554 | 本体前后相机视频流 |
| Web HTTP | 8080 | 状态查询、控制请求 |
| Web WebSocket | 8080 | 状态推送、视频流 |

## 快速开始

### 1. 部署

```bash
cd /opt/data/m20-patrol-robot
bash deploy/scripts/deploy-readonly.sh --one-shot
```

### 2. 验证

```bash
curl http://10.21.31.104:8080/api/v1/health
curl http://10.21.31.104:8080/api/v1/status/latest
```

### 3. 查看状态

访问 `http://10.21.31.104:8080/`

## 当前状态

| 能力 | 状态 |
|------|------|
| APDU/ASDU 编解码 | ✅ offline_verified |
| 状态订阅 | ✅ offline_verified |
| Web 服务 | ✅ offline_verified |
| 导航控制 | 🟡 需现场授权 |
| 运动控制 | 🔴 未实现 |
| 视频播放 | 🟡 待实测 |
| 多点巡逻 | 🔴 未实现 |
| 云台适配 | 🔴 待实物确认 |

## 测试

```bash
PYTHONPATH=. uv run --with pytest pytest -q
```

结果：169 passed

## 分支策略

- **main**：唯一工作分支
- 功能测试通过后方可考虑新分支
- 版本标签：`v0.1.0`（首个可用版本）

## 文档

详见 [docs/index.md](./docs/index.md)

## 协议依据

- 《山猫M20软件开发指南》V1.2.1（2026-05-18）— 协议优先依据
- 《山猫M20系列软件开发手册》V0.1.0（2025-09-16）— 导航字典参考

## 安全注意

- 导航/运动控制需负责人书面放行
- 不得后台自动下发控制指令
- 所有控制操作记录审计日志
- 模拟状态标识 `SIMULATED`，不得显示为真实

## 联系

项目协作通过 GitHub 私有仓库管理。
