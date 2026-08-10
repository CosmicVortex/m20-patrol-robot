# M20 Pro 巡逻机器人二次开发

M20 Pro 巡逻安防系统二次开发，部署于 GOS 主机，通过 basic_server 协议与 AOS 通信。

## 快速开始

### 部署（GOS 本机）

```bash
cd /opt/data/m20-patrol-robot
bash deploy/scripts/deploy-readonly.sh --one-shot
```

### 验证

```bash
curl http://10.21.31.104:8080/api/v1/health
curl http://10.21.31.104:8080/api/v1/status/latest
```

### 测试

```bash
cd /opt/data/m20-patrol-robot
PYTHONPATH=. uv run --with pytest pytest -q
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

- [部署流程](docs/06-deployment.md)
- [测试流程](docs/05-testing.md)
- [操作手册](docs/procedures/operations-manual.md)

## 状态

- 162 测试通过
- 云端离线基线完成
- 等待现场部署验证
