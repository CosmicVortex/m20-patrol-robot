# 05 — 测试流程

## 本地验证

### 运行全部测试

```bash
PYTHONPATH=. uv run --with pytest pytest -q
```

当前结果：**93 passed**（含 send_control 安全门禁测试）

### 编译检查

```bash
python3 -m compileall -q backend
```

### Diff 检查

```bash
git diff --check
```

### 部署脚本回归测试

```bash
bash deploy/tests/test-collect-readonly-info-addresses.sh
```

---

## 测试覆盖说明

| 模块 | 测试文件 | 覆盖内容 |
|---|---|---|
| protocol/frame | test_frame.py | 16字节帧编码/解码、粘包/拆包、非法同步字、长度边界 |
| protocol/messages | test_messages.py | JSON/XML信封编解码、Type/Command校验 |
| robot/status | test_status.py | 1002/3,4,5,6; 1007/1,2,3; 2002/1状态解析; 26个导航错误码 |
| robot/basic_client | test_basic_client.py | control_enabled门禁、message_id关联、连接拒绝 |
| navigation/v010 | test_navigation_v010.py | Gait值0x3002、门控验证、报文构造 |
| dashboard | test_dashboard.py | SIMULATED状态、127.0.0.1绑定 |

---

## 部署验证

GOS 部署后的验证步骤：

```bash
# 1. 检查服务状态
systemctl --user status m20-patrol-readonly.service --no-pager

# 2. 检查API响应
curl -fsS http://127.0.0.1:8080/api/v1/status/latest
# 预期：{"source": "SIMULATED", "connected": false, "control_enabled": false}

# 3. 检查页面标识
curl -fsS http://127.0.0.1:8080/ | grep 'SIMULATED / CONTROL OFF'
```

---

## 实机验收测试

### T1: 真实状态接入

- [ ] 连接 AOS basic_server TCP 30001
- [ ] 接收 1002/6 基础状态（MotionState/Gait/Charge/HES）
- [ ] 接收 1002/4 运控状态（Roll/Pitch/Yaw/速度）
- [ ] 接收 1002/5 设备状态（BatteryList/CPU温度/GPS）
- [ ] 接收 1002/3 异常列表（errorCode/component）
- [ ] 验证 message_id 关联正确

### T2: 视频接入

- [ ] 确认 RTSP 地址可达：`rtsp://10.21.31.103:8554/video1`
- [ ] 确认 RTSP 地址可达：`rtsp://10.21.31.103:8554/video2`
- [ ] GOS 转码为 HLS/WebRTC
- [ ] Web 端前后相机切换显示正常
- [ ] 记录延迟和流畅度

### T3: 单点导航控制

- [ ] 点击"前往点位"按钮
- [ ] 观察导航执行（到点、停止、状态反馈）
- [ ] 点击"停止"按钮
- [ ] 确认导航取消
- [ ] 检查审计日志

### T4: 异常处理

- [ ] 模拟定位丢失 → 自动暂停
- [ ] 触发急停 → 立即停止
- [ ] 低电量警告 → 拒绝新导航
- [ ] 断线重连 → 状态恢复

---

## 通过标准

- 所有测试项通过
- 异常停止可靠
- 审计日志完整
- 恢复机制正常
