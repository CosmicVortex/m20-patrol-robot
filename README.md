# M20 Pro 巡逻机器人系统

面向中升之星奔驰的机器狗安保巡逻系统，基于山猫 M20 Pro 机器狗二次开发。

[![Version](https://img.shields.io/badge/version-V1.1.3-blue.svg)](./CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-232%20passed-green.svg)](./backend/tests/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](./LICENSE)

**机型**: 山猫 M20 Pro  
**部署位置**: GOS 主机（10.21.31.104）  
**状态**: 🟡 offline_verified（待实机验证）

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

### 生产模式（部署后）

当前配置文件 `deploy/readonly-manifest.json` 设置为只读模式：

| 配置项 | 值 | 说明 |
|--------|-----|------|
| runtime_mode | realtime_readonly | 实时遥测只读 |
| read_only_mode | true | 禁止控制命令 |
| control_enabled | false | 禁用运动/导航控制 |
| telemetry_tx_enabled | false | 不发送心跳 |
| allow_real_io | false | 禁止真实IO |

### 本地测试模式

如需启用控制功能进行测试，修改配置文件：

```bash
# 编辑manifest
vim deploy/readonly-manifest.json

# 修改为测试模式
sed -i 's/"read_only_mode": true/"read_only_mode": false/' deploy/readonly-manifest.json
sed -i 's/"control_enabled": false/"control_enabled": true/' deploy/readonly-manifest.json
sed -i 's/"telemetry_tx_enabled": false/"telemetry_tx_enabled": true/' deploy/readonly-manifest.json
sed -i 's/"allow_real_io": false/"allow_real_io": true/' deploy/readonly-manifest.json
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

**部署文档**: [05-部署说明.md](./docs/项目文档/05-部署说明.md)
