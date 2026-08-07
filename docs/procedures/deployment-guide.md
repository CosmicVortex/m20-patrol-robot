# 办公室现场部署执行手册

**适用型号：** 山猫 M20 Pro
**部署地点：** 华翔智行办公室
**固件版本：** V1.1.8（已确认）
**AOS 地址：** 10.21.31.103（已确认）
**NOS 地址：** 10.21.31.106
**GOS 地址：** 10.21.31.104

---

## 一、部署前准备

### 1.1 设备清单

| 设备 | 数量 | 用途 |
|---|---|---|
| 山猫 M20 Pro | 1 | 巡逻本体 |
| GOS 主机 | 1 | 二次开发程序运行 |
| 笔记本电脑 | 1 | 部署管理、Web 监控 |
| 官方遥控器/APP | 1 | 导航基线测试 |

### 1.2 网络检查

```bash
# 在 GOS 上执行
ping -c 3 10.21.31.103  # AOS
ping -c 3 10.21.31.106  # NOS

# 检查 basic_server 端口
nc -zv 10.21.31.103 30001
nc -zv 10.21.31.103 30000
```

### 1.3 版本确认

```bash
# 在 NOS 上执行
ssh user@10.21.31.106 "cat /var/opt/robot/release_note.json"
```

预期输出包含：
- `software_version`: "V1.1.8"
- `firmware_version`: "V1.1.8" 或更高
- `aos_version`, `nos_version`, `gos_version`

### 1.4 地图备份

```bash
# 在 NOS 上执行
ssh user@10.21.31.106 "drmap pack"
ssh user@10.21.31.106 "ls -la /home/user/Downloads/*.zip"
ssh user@10.21.31.106 "sha256sum /home/user/Downloads/*.zip"
```

记录地图包文件名和 SHA-256。

---

## 二、GOS 部署流程

### 2.1 克隆仓库

```bash
# 在 GOS 上执行
cd ~
git clone /path/to/m20-patrol-robot.git
cd m20-patrol-robot
git checkout <APPROVED_COMMIT>
```

### 2.2 运行安装脚本

```bash
bash deploy/scripts/install-gos.sh \
  --repo "$PWD" \
  --ref $(git rev-parse HEAD)
```

### 2.3 验证安装

```bash
# 检查服务状态
systemctl --user status m20-patrol-realtime --no-pager

# 检查 API
curl -fsS http://127.0.0.1:8080/api/v1/status/latest | python3 -m json.tool

# 检查页面
curl -fsS http://127.0.0.1:8080/ | grep -E 'REAL|SIMULATED'
```

---

## 三、状态订阅验证

### 3.1 连接验证

```bash
# 查看实时日志
journalctl --user -u m20-patrol-realtime -f
```

预期日志：
```
INFO: Connecting to AOS 10.21.31.103:30001
INFO: Connected to AOS basic_server
INFO: Received basic_status (1002/6)
INFO: Received motion_status (1002/4)
INFO: Received device_status (1002/5)
```

### 3.2 API 验证

```bash
# 获取状态
curl -s http://127.0.0.1:8080/api/v1/status/latest | python3 -m json.tool
```

预期响应：
```json
{
  "source": "REAL",
  "connected": true,
  "control_enabled": false,
  "received_at": "2026-08-06T23:45:12+08:00",
  "age_ms": 120,
  "data": {
    "robot": "M20 Pro",
    "navigation": "SUBSCRIBING",
    "basic": {
      "MotionState": 17,
      "Gait": 12290,
      "Charge": 0
    },
    "motion": {
      "Roll": 0.12,
      "Pitch": -0.05,
      "Yaw": 45.2
    },
    "device": {
      "BatteryStatus": {
        "Left": {"BatteryLevel": 85},
        "Right": {"BatteryLevel": 87}
      }
    },
    "errors": []
  }
}
```

### 3.3 Web 页面验证

在浏览器访问 `http://10.21.31.104:8080/`（从笔记本访问）

检查项：
- [ ] 页面标题显示 "M20 巡逻状态"
- [ ] 右上角徽章显示 "REAL / CONTROL OFF"
- [ ] 连接状态显示 "已连接"
- [ ] 数据延迟 < 500ms
- [ ] 运动状态、步态、电量显示正确
- [ ] 异常列表为空或显示实际异常

---

## 四、视频接入验证

### 4.1 RTSP 可达性测试

```bash
# 测试前相机
ffprobe -v error -show_streams rtsp://10.21.31.103:8554/video1

# 测试后相机
ffprobe -v error -show_streams rtsp://10.21.31.103:8554/video2
```

预期输出包含：
- `codec_name`: h264 或 hevc
- `width`, `height`: 分辨率
- `r_frame_rate`: 帧率（如 30/1）

### 4.2 视频流启动

在 GOS 上测试 FFmpeg 拉流：

```bash
# 启动视频流（后台）
ffmpeg -hide_banner -loglevel warning \
  -i rtsp://10.21.31.103:8554/video1 \
  -c:v copy -an -f h264 pipe:1 \
  > /tmp/front.h264 &

# 检查进程
ps aux | grep ffmpeg

# 停止
kill %1
```

### 4.3 Web 端验证

在浏览器访问视频页面，检查：
- [ ] 前相机画面可显示
- [ ] 后相机画面可显示
- [ ] 画面切换正常
- [ ] 延迟 < 500ms

---

## 五、导航控制启用（需书面放行）

### 5.1 放行条件检查

- [ ] 现场负责人书面放行签字
- [ ] 安全观察员在场
- [ ] 急停按钮可用
- [ ] 隔离区域已设置
- [ ] 操作员已培训

### 5.2 启用导航控制

```bash
# 编辑服务配置
nano ~/.config/systemd/user/m20-patrol-realtime.service
```

修改 ExecStart 行，添加 `navigation_enabled=True`：

```ini
ExecStart=%h/m20-patrol-robot/.venv/bin/python -c 'from backend.app.dashboard_realtime import serve_dashboard; serve_dashboard(host="127.0.0.1", port=8080, aos_host="10.21.31.103", navigation_enabled=True)'
```

重载并重启：

```bash
systemctl --user daemon-reload
systemctl --user restart m20-patrol-realtime.service
```

### 5.3 Web 授权流程

1. 操作员登录 Web 页面
2. 点击"授权导航"按钮
3. 填写操作员姓名和备注
4. 系统检查安全条件：
   - control_enabled = true
   - TCP 已连接
   - 定位正常
   - 避障开启
   - 急停未触发
   - 无保护异常
   - 电量 ≥ 20%
   - 当前无导航任务
5. 授权成功后，徽章变为 "REAL / AUTHORIZED"

### 5.4 发送导航命令

1. 点击"前往点位"按钮
2. 输入坐标（PosX, PosY, PosZ, AngleYaw）
3. 点击"发送导航"
4. 系统发送 1003/1 命令
5. 机器人开始移动
6. 观察状态变化

### 5.5 取消导航

1. 点击"取消导航"按钮
2. 系统发送 1004/1 命令
3. 机器人停止移动
4. 查看审计日志确认

---

## 六、审计日志查看

```bash
# 通过 API 查看
curl -s http://127.0.0.1:8080/api/v1/navigation/audit | python3 -m json.tool
```

预期输出：
```json
{
  "audit_log": [
    {
      "timestamp": "2026-08-06T23:45:00+08:00",
      "action": "authorize",
      "details": "Operator: operator1, Note: Test navigation",
      "success": true
    },
    {
      "timestamp": "2026-08-06T23:46:00+08:00",
      "action": "send",
      "details": "Task 1: navigate to (1.0, 2.0)",
      "success": true
    },
    {
      "timestamp": "2026-08-06T23:47:00+08:00",
      "action": "cancel",
      "details": "Navigation cancelled",
      "success": true
    }
  ]
}
```

---

## 七、故障排查

### 7.1 服务无法启动

```bash
# 查看详细日志
journalctl --user -u m20-patrol-realtime -n 100 --no-pager

# 检查端口占用
netstat -tlnp | grep 8080

# 检查 Python 环境
ls -la ~/m20-patrol-robot/.venv/bin/python
```

### 7.2 无法连接 AOS

```bash
# 测试 TCP 连通性
nc -zv 10.21.31.103 30001

# 检查防火墙
sudo iptables -L -n | grep 30001

# 检查 basic_server 状态
ssh user@10.21.31.106 "systemctl --user status basic_server"
```

### 7.3 视频无法播放

```bash
# 检查编码格式
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 rtsp://10.21.31.103:8554/video1

# 检查 FFmpeg 编解码器
ffmpeg -codecs | grep -E 'h264|hevc'

# 测试本地播放
ffplay -autoexit rtsp://10.21.31.103:8554/video1
```

---

## 八、回滚流程

### 8.1 停止服务

```bash
systemctl --user stop m20-patrol-realtime.service
```

### 8.2 回滚到上一版本

```bash
bash deploy/scripts/rollback-gos.sh \
  --target-root "$HOME/.local/share/m20-patrol-robot" \
  --ref <PREVIOUS_COMMIT_SHA>
```

### 8.3 验证回滚

```bash
systemctl --user status m20-patrol-realtime --no-pager
curl -fsS http://127.0.0.1:8080/api/v1/status/latest
```

---

## 九、收尾工作

### 9.1 状态记录

填写以下记录表：

| 项目 | 值 |
|---|---|
| 部署时间 | |
| 部署人员 | |
| Commit SHA | |
| 固件版本 | |
| 地图文件名 | |
| 地图 SHA-256 | |
| 状态订阅 | 成功/失败 |
| 视频接入 | 成功/失败 |
| 导航控制 | 成功/失败 |
| 问题记录 | |

### 9.2 照片记录

拍摄以下照片：
- [ ] GOS 主机状态（指示灯、连接线）
- [ ] Web 页面显示（状态、视频）
- [ ] 机器人状态（运动、电量、异常）
- [ ] 导航执行过程

### 9.3 文档归档

将本次部署记录保存到：
```
docs/archive/deployments/YYYY-MM-DD-<site>-<commit>.md
```

---

## 十、安全提醒

- 导航控制启用前必须获得书面放行
- 操作员必须经过培训
- 安全观察员必须到场
- 急停按钮必须可用
- 所有操作必须记录审计日志
- 异常情况立即停止并回滚
