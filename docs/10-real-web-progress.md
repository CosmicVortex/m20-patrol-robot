# 10 — 集成进度

**更新时间：** 2026-08-09

## 已完成

| 模块 | 状态 | 测试 |
|------|------|------|
| 认证（auth/） | ✅ | test_auth_*.py |
| API路由（api/） | ✅ | test_api_*.py |
| 配置加载（config.py） | ✅ | test_config.py |
| 协议编解码（protocol/） | ✅ | test_frame.py, test_messages.py |
| 状态解析（robot/status.py） | ✅ | test_status.py |
| TCP客户端（robot/basic_client.py） | ✅ | test_basic_client.py |
| 遥测适配器（robot/telemetry.py） | ✅ | test_telemetry.py |
| 导航报文（navigation/v010.py） | ✅ | test_navigation_v010.py |
| Web服务（server.py） | ✅ | 模块导入验证 |
| 部署脚本 | ✅ | deploy/tests/ |

**当前测试：169 passed**

## 待现场接入

| 能力 | 前置条件 |
|------|----------|
| 真实遥测 | AOS TCP 30001 连通 |
| 视频播放 | RTSP URL、ffprobe、浏览器首帧 |
| 导航控制 | 负责人书面放行、安全快照 |
| 运动控制 | 逐项现场授权 |

## 当前状态

- 云端离线验证：✅ 完成
- GOS真机部署：pending
- 现场验收：pending

详见 [09-real-web-integration-contract.md](./09-real-web-integration-contract.md)
