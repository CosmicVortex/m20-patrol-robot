# M20 Pro 真实 Web 与 GOS 部署就绪审计报告

**审计日期：** 2026-08-09  
**项目：** m20-patrol-robot  
**目标：** M20 Pro / 东莞中升奔驰现场，只读遥测 Web 与媒体/地图界面  
**主要依据：** 用户确认的《山猫M20软件开发指南》V1.2.1（2026-05-18）、仓库 `docs/official/`、`docs/09-real-web-integration-contract.md`、当前代码与部署脚本

## 最终结论

**状态：BLOCKED_FOR_FIELD_DEPLOYMENT**

当前版本已完成代码级修复和云端离线验证，但不能宣称已完成 GOS 真机部署、AOS 运行集成、视频首帧验证、奔驰 4S 店地图导入或现场验收。

可确认的状态：

- `implemented`：协议解析、只读 TCP 适配器、Web 服务骨架、认证基础模块、部署脚本、当前深色四路视频/地图占位界面
- `offline_verified`：当前离线测试 169 passed，Python 编译、Shell 语法、HTML/JS 检查通过
- `runtime_integrated`：pending，云端没有 GOS/AOS 现场输出
- `field_verified`：pending
- `field_accepted`：pending
- `video`：unverified / blocked pending 现场 RTSP、ffprobe、浏览器首帧证据
- `map`：blocked pending 东莞中升奔驰现场地图图片/地图包/坐标标定
- `control`：blocked，当前只读关闭

## 本轮已修复的代码级问题

1. `ConfigLoader` 已兼容部署 manifest 的嵌套字段：
   - `web_bind_host`
   - `targets.aos_host`
   - `ports.aos_tcp/web`
   - `stale_after_seconds`
   - `telemetry_rx_enabled`
2. 真实 Web systemd 单元已改为启动：
   - `python -m backend.app.server --manifest ...`
   - 不再直接启动旧的独立 `dashboard_realtime.py` 页面
3. Web server 已实际挂载当前 `docs/website/index.html` 静态首页
4. API router 已修复为在真实请求 handler 上调用 API handler；此前 detached handler 会导致 `_parse_json_body`、`_authenticate` 和响应方法缺失
5. 登录响应已在发送响应头前正确设置 Cookie
6. 状态 API 返回原始状态 payload，兼容部署健康检查字段
7. 无 `M20_ADMIN_PASSWORD` 时不再自动创建已知固定密码账户
8. 模拟模式仍提供明确的 `SIMULATED/NO_DATA` 状态 API，不让状态端点消失
9. 当前地图 UI 已移除地图网格和图例，仅保留纯占位提示，不绘制任何未确认区域、路线、点位、告警或充电桩
10. 部署回归测试已修正，避免 `pipefail` 下因 `grep -q` 提前关闭管道造成假失败

## 已执行验证

```text
PYTHONPATH=. uv run --with pytest pytest -q --tb=short
169 passed in 5.02s

python3 -m compileall -q backend
PASS

Python 3.8 AST parse check
PASS

bash -n deploy/scripts/*.sh deploy/tests/*.sh
PASS

git diff --check
PASS

bash deploy/scripts/deploy-readonly.sh --dry-run
DRY_RUN=true
NO_FILES_WRITTEN=true
NO_SYSTEMD_CHANGE=true
NO_NETWORK_SIDE_EFFECT=true

bash deploy/tests/test-collect-readonly-info-addresses.sh
PASS

bash deploy/tests/test-install-gos-venv.sh
PASS

本地 HTTP smoke test（Python 3.13，仅验证运行 wiring）
首页 HTTP 200，当前 M20 Pro Mercedes 4S 页面可返回
登录 HTTP 200
状态 API HTTP 200，source=SIMULATED，control_enabled=false，telemetry_tx_enabled=false
健康检查 HTTP 503，原因是当前没有真实遥测，这是正确的 fail-closed 行为
```

## 当前真实能力矩阵

| 能力 | 状态 | 证据 | 现场缺口 |
|---|---|---|---|
| APDU/ASDU 编解码 | offline_verified | 协议/帧测试通过 | 无真实报文样本 |
| 状态解析 | offline_verified | 1002/3、4、5、6、1007、2002 等测试 | 无真实软件版本和报文 |
| AOS TCP 只读接收 | implemented / offline_verified | `BasicServerClient`、`TelemetryAdapter` | 未在 GOS/AOS 建立连接 |
| Web 服务入口 | implemented / offline_verified | `backend.app.server` + systemd 模板 | 未在 GOS 启动 |
| Web 首页 | implemented / offline_verified | 首页 smoke test HTTP 200 | 尚未由 GOS 服务提供 |
| 认证 | implemented / offline_verified | PBKDF2、Session、Cookie smoke test | 需现场管理员初始化与安全策略确认 |
| `/api/v1/status/latest` | implemented / offline_verified | 模拟状态 smoke test | 需 `REAL_FRESH` 现场输出 |
| 健康检查 | implemented / offline_verified | 模拟无数据返回 503 | 需现场 source=REAL、valid_frames>0、新鲜数据 |
| 四路视频墙 | UI implemented | 当前页面明确 UNVERIFIED/BLOCKED | 仅文档默认 video1/video2，热成像/主码流未确认 |
| RTSP/浏览器媒体 | framework/blocked | 无 Web media route、无 `<video>` 首帧 | 需 RTSP URL、鉴权、ffprobe、浏览器首帧 |
| 截图/录像 | not_implemented | 当前无完整 HTTP 媒体 API 和存储链路 | 需另行实现并现场验证 |
| 奔驰 4S 店地图 | placeholder implemented | 纯占位，拒绝伪造地图 | 需现场地图图片/包、SHA-256、坐标标定 |
| 导航状态 | partial/offline_verified | 协议 primitive 存在 | API 目前 unverified/TODO，不能真机下发 |
| 导航/运动控制 | blocked | control=false、TX=false、API fail-closed | 需负责人授权、安全快照、急停和现场放行 |
| AI告警/工单/轨迹/数字孪生/设备档案/设置 | UI label only | 无真实数据路由和持久化实现 | 不得宣称功能完成 |

## 未解决的现场阻塞项

1. 未取得 GOS `10.21.31.104` 的原始现场输出
2. 未取得 AOS `10.21.31.103:30001` TCP 连通、接收字节、有效帧、解析和状态接受证据
3. 云端无 `python3.8`，不能替代 GOS Python 3.8.10 运行验证
4. 云端无 GOS systemd user manager，不能验证实际 user unit 生命周期
5. 未取得 M20 Pro 实机软件/固件/协议服务版本
6. 未取得现场 RTSP/WebRTC 媒体源、鉴权、编解码、分辨率、帧率和首帧证据
7. 未取得东莞中升奔驰现场地图图片、地图包、坐标系、地图 ID 和标定结果
8. 当前工作树仍为 dirty，不能直接走正式 `--one-shot` immutable release 门禁
9. 旧 `deploy/systemd/m20-patrol-realtime.service` 仍存在硬编码旧入口，虽然正式只读部署会检查它 inactive/disabled，但仍需在发布前删除或明确隔离
10. 部署脚本仍需在 GOS 现场验证 user service、rendered unit、回滚和健康门禁

## GOS 现场只读验证顺序

在用户本地笔记本/GOS 执行，返回完整原始输出。不要执行导航、运动、定位重置、充电或任何控制命令。

### A. 主机和版本

```bash
hostname; id; uname -a; python3.8 --version
ip -4 addr; ip route
command -v ffprobe; ffprobe -version | head -1
systemctl --user show-environment
```

### B. AOS 只读网络证据

```bash
nc -zvw3 10.21.31.103 30001
nc -zvw3 10.21.31.103 8554
```

### C. 代码包验证

```bash
sha256sum <deployment-package.zip>
python3.8 -m compileall -q backend
PYTHONPATH=. python3.8 -m pytest -q
```

### D. 只读部署前置

```bash
bash deploy/scripts/deploy-readonly.sh --preflight
```

只有返回目标身份、Python 3.8.10、systemd user、冲突服务状态和 `PREFLIGHT=PASS`，才可继续。仍需保留所有原始输出。

### E. 启动后严格健康证据

```bash
curl -i http://10.21.31.104:8080/api/v1/health
curl -i http://10.21.31.104:8080/api/v1/status/latest
systemctl --user status m20-patrol-readonly.service --no-pager
journalctl --user -u m20-patrol-readonly.service -n 200 --no-pager
```

只有同时满足以下条件，才可写入 `runtime_integrated`：

- `runtime_mode=realtime_readonly`
- `read_only_mode=true`
- `control_enabled=false`
- `telemetry_tx_enabled=false`
- `source=REAL`
- `connected=true`
- `valid_frames>0`
- `frame_valid=true`
- `message_parsed=true`
- `status_accepted=true`
- `telemetry_fresh=true`
- `data_state=REAL_FRESH`
- `0 <= age_ms < stale_after_seconds*1000`

## 禁止的结论

在收到上述 GOS/AOS 原始输出前，不得写：

- “已部署完成”
- “实时数据已接入”
- “视频已在线”
- “地图已导入”
- “机器狗在线”
- “巡检任务可执行”
- “导航控制已完成”
- “可量产部署”

## 审计结论

当前代码已经从“明显运行 wiring 断裂”推进到“云端离线验证通过、可交给 GOS 做只读联调前置”的状态，但仍是：

```text
BLOCKED_FOR_FIELD_DEPLOYMENT
runtime_integrated: pending
field_verified: pending
field_accepted: pending
video: blocked/unverified
map: blocked
control: blocked
```
