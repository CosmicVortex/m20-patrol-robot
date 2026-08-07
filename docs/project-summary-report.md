# 山猫 M20 Pro 巡逻安防系统 — 深度项目总结报告

**报告日期：** 2026-08-07
**代码版本：** a550839
**手册依据：** V1.2.1 (2026-05-18)
**测试状态：** 93 passed

---

## 一、项目背景

### 1.1 项目目标

在云深处山猫 M20 Pro 机器狗上实现巡逻安防系统的二次开发，部署在 GOS（用户开发主机）上，通过 basic_server 协议与 AOS（运动控制主机）通信，提供：

- 实时状态监控（运动状态、电量、异常、定位）
- 本体前后相机视频回传
- Web 人工单点导航控制（授权后）

### 1.2 项目范围

**纳入范围：**
- M20 Pro 本体前后相机视频回传
- 实时状态监控
- Web 人工单点导航控制（授权后）
- 办公室 → 门店两阶段部署

**不纳入范围：**
- AOS/NOS 原厂服务修改
- 数尔安防云台/视频适配（待后续独立开发）
- S10 平台适配（待办公室验收后评估）
- 16台统一管理（待后续阶段）

### 1.3 场地顺序

```
阶段1：华翔智行办公室
  ├─ 建图、定位核验
  ├─ 遥控器/APP 自主导航基线
  ├─ 状态接入、视频切换
  ├─ Web 单点导航控制
  └─ 验收通过后迁移

阶段2：东莞中升之星奔驰 4S 店
  ├─ 重新建图（不得复用办公室地图）
  ├─ 重新采集点位
  └─ 重新验收
```

### 1.4 关键约束

1. `control_enabled=false` 为默认值，真实连接必须显式启用
2. 导航发送前必须满足：型号确认、版本兼容、权限批准、真实样本、状态正常、书面放行
3. 所有地址、端口为候选值，必须现场签认（AOS 地址已确认：10.21.31.103）
4. 模拟状态标注 `SIMULATED`，不得伪装为真实设备状态

---

## 二、当前建设情况

### 2.1 代码实现状态

| 模块 | 文件 | 状态 | 测试数 |
|---|---|---|---|
| APDU/ASDU 编解码 | `protocol/frame.py`, `messages.py` | ✅ 已实现 | 8 tests |
| 状态消息解析 | `robot/status.py` | ✅ 已实现 | 11 tests |
| TCP 客户端 + 门禁 | `robot/basic_client.py` | ✅ 已实现 | 4 tests |
| **真实状态订阅** | `robot/telemetry.py` | ✅ 已实现 | 6 tests |
| 导航报文构造 | `navigation/v010.py` | ✅ 已实现 | 10 tests |
| **导航控制服务** | `navigation/service.py` | ✅ 已实现 | 7 tests |
| 视频流管理器 | `video/stream_manager.py` | 🟡 基础框架 | — |
| WebSocket 处理器 | `video/ws_handler.py` | 🟡 基础框架 | — |
| 模拟仪表盘 | `dashboard.py` | ✅ 已实现 | 2 tests |
| **实时仪表盘** | `dashboard_realtime.py` | ✅ 已实现 | — |
| **简化版仪表盘** | `dashboard_simple.py` | ✅ 已实现 | Python 3.8 兼容 |
| 安装脚本 | `deploy/scripts/install-gos.sh` | ✅ 已实现 | — |
| 回滚脚本 | `deploy/scripts/rollback-gos.sh` | ✅ 已实现 | — |

**总计：** 18 个应用代码文件，11 个测试文件，93 个测试用例全部通过。

### 2.2 官方资料库

共 19 份官方文档（3 PDF + 16 Markdown）：

| 类型 | 数量 | 版本 |
|---|---|---|
| 核心协议依据 | 1 份 | V1.2.1 (2026-05-18) |
| 系统架构说明 | 1 份 | V1.0.0 (2026-06-18) |
| 功能接口文档 | 7 份 | V1.0.0 (2026-06-18) |
| 开发教程 | 2 份 | V0.1.1 (2025-12-24) |
| 参考文档 | 5 份 | V1.0.0 (2026-06-18) |
| 产品手册 | 1 份 | V1.1.0 |
| 使用手册 | 1 份 | V0.0.1 (2025-07-31) |
| 开发者文档总览 | 1 份 | V1.0.0 (2026-06-18) |
| ROS2/DDS 接口 | 1 份 | V1.0.0 (2026-06-18) |

### 2.3 需求完成度

| 需求 | 状态 | 完成度 |
|---|---|---|
| R-01 APDU 16字节帧编解码 | ✅ 已实现 | 100% |
| R-02 JSON/XML PatrolDevice 信封 | ✅ 已实现 | 100% |
| R-03 模拟只读状态页面 | ✅ 已实现 | 100% |
| R-04 GOS 现场只读核验 | 🟡 脚本已实现 | 70% |
| R-05 可重复安装、停止和回滚 | ✅ 已实现 | 100% |
| R-06 真实状态连接与解析 | ✅ 已实现 | 90% |
| R-07 双路视频接入 | 🟡 基础框架已实现 | 40% |
| R-08 单点导航接口 | 🟡 已实现 Web 授权控制 | 60% |
| R-09 多点巡逻和 Web 控制 | 🔴 未实现 | 0% |
| R-10 云台、照片和告警 | 🔴 未实现 | 0% |

---

## 三、代码与官方手册契合度核对

### 3.1 协议头部（V1.2.1 §1.1.5）

| 字段 | 手册定义 | 代码实现 | 状态 |
|---|---|---|---|
| 同步字符 | EB 91 EB 90 | `frame.py:238` | ✅ |
| 长度（小端） | 2字节 | `frame.py:240` | ✅ |
| 报文ID（小端） | 2字节 | `frame.py:241` | ✅ |
| ASDU格式位 | 1字节（XML=0, JSON=1） | `frame.py:242` | ✅ |
| 预留7字节 | 0x00 | `frame.py:248` | ✅ |
| 头部总长 | 16字节 | `frame.py:243` | ✅ |

### 3.2 状态消息解析（V1.2.1 §1.3）

| 消息类型 | 命令码 | 代码位置 | 状态 |
|---|---|---|---|
| BasicStatus | 1002/6 | `status.py:114` | ✅ |
| MotionStatus | 1002/4 | `status.py:116` | ✅ |
| DeviceStatus | 1002/5 | `status.py:118` | ✅ |
| ErrorList | 1002/3 | `status.py:120` | ✅ |
| 位置查询 | 1007/2 | `status.py:101` | ✅ |
| 感知查询 | 2002/1 | `status.py:103` | ✅ |
| 导航异常上报 | 1007/3 | `status.py:108` | ✅（≥V1.1.8） |

### 3.3 导航消息（V1.2.1 §1.4）

| 消息类型 | 命令码 | 代码位置 | 状态 |
|---|---|---|---|
| 导航下发 | 1003/1 | `v010.py:116` | ✅ |
| 导航取消 | 1004/1 | `v010.py:137` | ✅ |
| 导航状态 | 1007/1 | `status.py:105` | ✅ |

### 3.4 关键值对齐

| 项目 | V0.1.0 | V1.2.1 | 代码 | 状态 |
|---|---|---|---|---|
| 平地步态 | 12 | 0x3002 | `v010.py:18` | ✅ |
| 楼梯步态 | 13 | 0x3003 | `v010.py:19` | ✅ |
| 基础步态 | 1 | 0x1001 | `v010.py:20` | ✅ |
| 高台步态 | 2 | 0x1002 | `v010.py:21` | ✅ |
| 导航错误码数量 | — | 26个 | `status.py:47-86` | ✅ |
| 1007/3 导航异常上报 | 不支持 | ≥V1.1.8 | `status.py:240` | ✅ |

### 3.5 已修复的阻塞项

| 阻塞项 | 问题 | 修复方案 | 状态 |
|---|---|---|---|
| message_id 关联 | TCP 响应按 message_type+command 匹配，可能误判延迟响应 | PatrolMessage 新增 message_id 字段，按 ID 匹配 | ✅ 已修复 |
| control_enabled 门禁 | connect() 允许在 control_enabled=False 时连接 | connect() 检查 control_enabled，False 时拒绝真实连接 | ✅ 已修复 |
| 安装回滚 | GOS 安装事务在服务启动、current 链接和失败回滚之间尚未完全闭环 | rollback-gos.sh 保存前置状态并自动恢复 | ✅ 已修复 |

---

## 四、主机角色与网络架构

### 4.1 主机角色

| 主机 | IP（已确认） | 职责 | SSH/VNC |
|---|---|---|---|
| AOS | 10.21.31.103 | 运动控制、basic_server、rl_deploy | ❌ 不可访问 |
| NOS | 10.21.31.106 | 建图、定位、导航、planner | ✅ 可访问 |
| GOS | 10.21.31.104 | 用户二次开发、Web 服务 | ✅ 可访问 |

### 4.2 协议端口

| 接口 | 协议 | 端口 | 用途 |
|---|---|---|---|
| basic_server TCP | APDU/ASDU JSON | 30001 | 任务下发、状态订阅（推荐） |
| basic_server UDP | APDU/ASDU JSON | 30000 | 高频速度指令（≥20Hz） |
| RTSP | H.265/H.264 | 8554 | 本体前后相机视频 |
| Web HTTP | JSON | 8080 | 状态查询、控制请求 |
| Web WebSocket | — | 8080 | 状态推送、视频流 |
| ROS2/DDS | FastDDS | 动态 | 话题订阅（GOS 内部） |

### 4.3 RTSP 视频地址

| 相机 | 地址 | 状态 |
|---|---|---|
| 前广角 | `rtsp://10.21.31.103:8554/video1` | 🟡 待实测 |
| 后广角 | `rtsp://10.21.31.103:8554/video2` | 🟡 待实测 |

---

## 五、后续实施方案

### 5.1 办公室现场执行（按顺序）

#### 第一阶段：版本与网络确认

```bash
# 1. 版本确认（在 NOS 上执行）
ssh user@10.21.31.106 "cat /var/opt/robot/release_note.json"

# 2. 网络连通性测试（在 GOS 上执行）
ping -c 3 10.21.31.103  # AOS
ping -c 3 10.21.31.106  # NOS

# 3. TCP 端口测试
nc -zv 10.21.31.103 30001
nc -zv 10.21.31.103 30000
```

#### 第二阶段：地图备份与定位核验

```bash
# 4. 地图备份（在 NOS 上执行）
ssh user@10.21.31.106 "drmap pack"
ssh user@10.21.31.106 "sha256sum /home/user/Downloads/*.zip"

# 5. 定位核验（在 NOS 上执行）
ssh user@10.21.31.106 "readlink -f /var/opt/robot/data/maps/active"
```

#### 第三阶段：RTSP 视频测试

```bash
# 6. 测试 RTSP 可达性（在 GOS 上执行）
ffprobe -v error -show_streams rtsp://10.21.31.103:8554/video1
ffprobe -v error -show_streams rtsp://10.21.31.103:8554/video2
```

记录：
- 编码格式（H.264 或 H.265）
- 分辨率（width/height）
- 帧率（r_frame_rate）

#### 第四阶段：GOS 部署

```bash
# 7. 部署服务（在 GOS 上执行）
bash deploy/scripts/install-gos.sh \
  --repo "$PWD" \
  --ref a550839

# 8. 验证服务状态
systemctl --user status m20-patrol-realtime --no-pager

# 9. 验证 API 响应
curl -fsS http://127.0.0.1:8080/api/v1/status/latest | python3 -m json.tool
```

#### 第五阶段：书面放行与导航启用

```bash
# 10. 修改服务配置启用导航控制
nano ~/.config/systemd/user/m20-patrol-realtime.service
# 添加 navigation_enabled=True

# 11. 重启服务
systemctl --user daemon-reload
systemctl --user restart m20-patrol-realtime.service
```

#### 第六阶段：Web 授权与导航测试

1. 操作员登录 Web 页面 `http://10.21.31.104:8080/`
2. 点击"授权导航"按钮，填写操作员姓名
3. 系统检查安全条件：
   - control_enabled = true
   - TCP 已连接
   - 定位正常
   - 避障开启
   - 急停未触发
   - 无保护异常
   - 电量 ≥ 20%
   - 当前无导航任务
4. 点击"前往点位"，输入坐标
5. 系统发送 1003/1 导航命令
6. 观察机器人移动
7. 点击"取消导航"停止
8. 查看审计日志确认操作记录

### 5.2 办公室验收检查清单

- [ ] AOS 版本确认为 V1.1.8 或更高
- [ ] 地图已备份，SHA-256 已记录
- [ ] RTSP 视频可达，编码格式已确认
- [ ] 状态订阅正常工作（source=REAL, connected=true）
- [ ] Web 页面正常显示（REAL / CONTROL OFF）
- [ ] 书面放行已获取
- [ ] 导航控制可启用
- [ ] 单点导航执行正常
- [ ] 审计日志记录完整
- [ ] 异常停止机制正常

### 5.3 东莞门店迁移（办公室验收通过后）

1. 清理办公室地图引用
2. 重新建图（不得复制办公室地图）
3. 重新采集点位
4. 重新验收
5. 记录新地图身份和 SHA-256

---

## 六、安全风险控制

### 6.1 控制边界

| 控制项 | 默认状态 | 启用条件 |
|---|---|---|
| control_enabled | False | Web UI 显式授权 |
| 导航命令发送 | 禁止 | 书面放行 + 安全门控通过 |
| 运动控制命令 | 禁止 | 书面放行 + 安全门控通过 |
| 心跳发送 | 允许 | 仅用于状态订阅 |

### 6.2 安全门控条件

导航命令发送前必须满足：

1. control_enabled = true
2. field_authorization 非空
3. tcp_connected = true
4. location_normal = true
5. obstacle_avoidance_active = true
6. hard_estop_active = false
7. protective_fault_active = false
8. battery_percent ≥ 20
9. active_task = false

### 6.3 异常处理

| 异常类型 | 处理方式 |
|---|---|
| 连接断线 | 自动重连（指数退避） |
| 数据超时 | 标记为 stale，页面显示重连中 |
| 导航异常 | 自动取消任务，记录审计日志 |
| 急停触发 | 立即停止所有控制，重新授权 |

---

## 七、测试验证

### 7.1 测试统计

```
93 passed in 2.27s
compileall 通过
git diff --check 通过
```

### 7.2 测试覆盖

| 模块 | 测试文件 | 测试数 |
|---|---|---|
| APDU 帧编解码 | test_frame.py | 8 |
| ASDU 信封编解码 | test_messages.py | 3 |
| 状态消息解析 | test_status.py | 11 |
| TCP 客户端门禁 | test_basic_client.py | 4 |
| TCP 传输层 | test_basic_tcp_transport.py | 2 |
| 导航报文构造 | test_navigation_v010.py | 10 |
| 导航命令 | test_navigation_commands_v010.py | 6 |
| 导航服务 | test_navigation_service.py | 7 |
| 视频资源 | test_site_assets.py | 5 |
| **TelemetryAdapter** | **test_telemetry.py** | **6** |
| 模拟仪表盘 | test_dashboard.py | 2 |

---

## 八、文档体系

### 8.1 当前文档结构

```
docs/
├── 00-index.md              # 导航入口
├── 01-overview.md           # 项目概览
├── 02-architecture.md       # 系统架构
├── 03-modules.md            # 模块说明
├── 04-requirements.md       # 需求清单
├── 05-testing.md            # 测试流程
├── 06-deployment.md         # 部署流程
├── 07-changes.md            # 变更记录
│
├── procedures/              # 现场操作手册
│   ├── deployment-guide.md  # 部署执行手册
│   ├── mapping-test.md      # 建图测试
│   └── office-acceptance.md # 办公室验收
│
├── reviews/                 # 审查记录
│   ├── v121-alignment.md    # V1.2.1 对齐
│   └── blockers-fixed.md    # 阻塞项修复
│
├── official-docs-review.md  # 官方资料台账
│
└── official/                # 官方文档（19份，只读）
```

### 8.2 关键文档说明

| 文档 | 用途 | 读者 |
|---|---|---|
| 01-overview.md | 项目目标、范围、安全规则 | 所有人 |
| 02-architecture.md | 系统架构、主机角色、协议接口 | 架构师、开发者 |
| 03-modules.md | 代码模块职责说明 | 开发者 |
| 04-requirements.md | 需求状态、验收条件 | 项目经理、审查人员 |
| 05-testing.md | 测试流程、验证方法 | 测试人员 |
| 06-deployment.md | 部署步骤、故障排查 | 现场工程师 |
| procedures/deployment-guide.md | **办公室现场执行手册** | **现场工程师** |

---

## 九、版本历史

| 版本 | 日期 | 变更内容 |
|---|---|---|
| V0.1 | 2026-08-05 | 初始基线：协议编解码、状态解析、导航报文构造、模拟仪表盘 |
| V0.2 | 2026-08-06 | 文档架构重构、1007/3 导航异常上报解析 |
| V0.3 | 2026-08-06 | 真实状态订阅、实时仪表盘 |
| **V0.4** | **2026-08-07** | **视频接入框架、导航控制服务（Web 授权）** |

---

## 十、结论

### 10.1 当前状态

- ✅ 协议编解码、状态解析、导航报文构造全部离线验证通过
- ✅ 19 份官方文档已入库
|- ✅ 93 个测试用例全部通过
- ✅ 三个代码阻塞项已全部修复
- ✅ AOS 地址已确认（10.21.31.103）
- ✅ 固件版本要求已确认（V1.1.8）
- ✅ 视频接入已授权
- ✅ 导航控制需 Web 授权 + 书面放行

### 10.2 待现场执行

- [ ] 版本确认（V1.1.8 或更高）
- [ ] 地图备份（drmap pack + SHA-256）
- [ ] RTSP 视频参数实测
- [ ] GOS 部署与服务验证
- [ ] 书面放行
- [ ] Web 导航控制闭环测试

### 10.3 后续工作

1. 完成办公室阶段验收（9 项检查清单）
2. 东莞门店重新建图与部署
3. 评估 S10 平台适配可行性
4. 云台 SR-UPA810T609 接口开发
5. 多点巡逻状态机实现

---

**报告编制：** 贾维斯
**审核状态：** 待现场验证
**下一版本：** V0.5（办公室验收通过后）
