# 06 — 部署流程

## GOS 前置条件

由现场负责人确认：

- 使用非 root 账户
- Python 3 可用，且支持 `venv`
- `systemctl --user` 可用，且用户服务管理器已启动
- release 验证所需的 pytest 可用
- 安装目录有写权限
- 现场已批准仓库和 commit
- 不需要访问机器人网络即可完成本次模拟部署

如需执行现场只读核验，先使用 `deploy/scripts/collect-readonly-info.sh`，只填写已批准的 AOS/GOS/NOS 地址。

---

## 模式说明

| 模式 | 服务文件 | 状态来源 | 控制权限 | 适用场景 |
|---|---|---|---|---|
| 模拟只读 | `m20-patrol-readonly.service` | SIMULATED | 无 | 离线基线部署 |
| 真实状态 | `m20-patrol-realtime.service` | REAL | 无 | 现场状态订阅 |
| 完整功能 | 同真实状态 | REAL | Web 授权 | 书面放行后启用 |

---

## 安装

### 方式一：模拟只读模式（无需放行）

在已经检出的仓库目录执行：

```bash
bash deploy/scripts/install-gos.sh \
  --repo "$PWD" \
  --ref <APPROVED_COMMIT_SHA>
```

脚本执行内容：

1. 校验完整 commit SHA 存在
2. 将 commit 导出到独立 release 目录
3. 创建虚拟环境
4. 使用批准环境中的 pytest 执行离线测试；pytest 不可用时直接失败
5. 执行 Python 编译检查
6. 写入并校验用户级 systemd 服务
7. 启动模拟只读服务
8. 服务启动成功后更新 `current` 软链接

脚本不会执行 `git fetch`、网络探测、机器人连接或控制操作。

### 方式二：真实状态订阅（需现场放行）

安装后修改 systemd 服务配置：

```bash
# 编辑服务配置
nano ~/.config/systemd/user/m20-patrol-realtime.service
```

确认配置：

```ini
[Service]
ExecStart=%h/m20-patrol-robot/.venv/bin/python -c 'from backend.app.dashboard_realtime import serve_dashboard; serve_dashboard(host="127.0.0.1", port=8080, aos_host="10.21.31.103")'
```

重载并启动：

```bash
systemctl --user daemon-reload
systemctl --user start m20-patrol-realtime.service
systemctl --user enable m20-patrol-realtime.service
```

### 方式三：启用导航控制（需书面放行）

修改服务配置，添加 `navigation_enabled=True`：

```bash
# 编辑服务配置
nano ~/.config/systemd/user/m20-patrol-realtime.service
```

```ini
[Service]
ExecStart=%h/m20-patrol-robot/.venv/bin/python -c 'from backend.app.dashboard_realtime import serve_dashboard; serve_dashboard(host="127.0.0.1", port=8080, aos_host="10.21.31.103", navigation_enabled=True)'
```

重载并重启：

```bash
systemctl --user daemon-reload
systemctl --user restart m20-patrol-realtime.service
```

---

## 验证

### 模拟只读模式验证

```bash
# 检查服务状态
systemctl --user status m20-patrol-readonly.service --no-pager

# 检查API响应
curl -fsS http://127.0.0.1:8080/api/v1/status/latest
# 预期：{"source": "SIMULATED", "connected": false, "control_enabled": false}

# 检查页面标识
curl -fsS http://127.0.0.1:8080/ | grep 'SIMULATED / CONTROL OFF'
```

### 真实状态模式验证

```bash
# 检查服务状态
systemctl --user status m20-patrol-realtime.service --no-pager

# 检查API响应
curl -fsS http://127.0.0.1:8080/api/v1/status/latest
# 预期：{"source": "REAL", "connected": true, "control_enabled": false}

# 检查页面标识
curl -fsS http://127.0.0.1:8080/ | grep 'REAL / CONTROL OFF'
```

### 导航控制模式验证

```bash
# 检查导航服务状态
curl -fsS http://127.0.0.1:8080/api/v1/navigation/status
# 预期：{"authorized": false, "control_enabled": true, ...}

# 检查页面标识
curl -fsS http://127.0.0.1:8080/ | grep 'REAL / AUTHORIZED'
```

---

## 停止与回滚

### 停止服务

```bash
systemctl --user stop m20-patrol-realtime.service
systemctl --user disable m20-patrol-realtime.service
```

### 回滚到上一版本

```bash
bash deploy/scripts/rollback-gos.sh \
  --target-root "$HOME/.local/share/m20-patrol-robot" \
  --ref <PREVIOUS_COMMIT_SHA>
```

回滚脚本会：
1. 保存当前状态（链接、服务文件）
2. 停止当前服务
3. 卸载当前 release
4. 恢复上一版本
5. 启动上一版本服务
6. 验证回滚结果

---

## 现场执行检查清单

### 部署前检查

- [ ] GOS 账户可用，非 root
- [ ] Python 3 可用：`command -v python3`
- [ ] systemd 用户管理器可用：`systemctl --user show-environment`
- [ ] pytest 可用：`python3 -m pytest --version`
- [ ] ffprobe 可用（视频接入）：`command -v ffprobe`
- [ ] ffmpeg 可用（视频转码）：`command -v ffmpeg`
- [ ] 仓库已检出，commit SHA 已确认
- [ ] 现场负责人已批准部署

### 部署后验证

- [ ] 服务启动成功：`systemctl --user status m20-patrol-realtime`
- [ ] API 响应正常：`curl http://127.0.0.1:8080/api/v1/status/latest`
- [ ] Web 页面可访问：`curl http://127.0.0.1:8080/`
- [ ] 状态数据源正确：`"source": "REAL"` 或 `"SIMULATED"`
- [ ] 连接状态正确：`"connected": true` 或 `false`
- [ ] 控制开关正确：`"control_enabled": false`（默认）

### RTSP 视频测试

```bash
# 测试前相机
ffprobe -v error -show_streams rtsp://10.21.31.103:8554/video1

# 测试后相机
ffprobe -v error -show_streams rtsp://10.21.31.103:8554/video2
```

预期输出包含：
- `codec_name`：h264 或 hevc
- `width`/`height`：分辨率
- `r_frame_rate`：帧率

---

## 故障排查

### 服务无法启动

```bash
# 查看详细日志
journalctl --user -u m20-patrol-realtime -n 50 --no-pager

# 检查端口占用
netstat -tlnp | grep 8080

# 检查 Python 环境
ls -la ~/m20-patrol-robot/.venv/bin/python
```

### 无法连接 AOS

```bash
# 测试 TCP 连通性
nc -zv 10.21.31.103 30001

# 测试 RTSP 连通性
ffprobe -v error -show_format rtsp://10.21.31.103:8554/video1

# 检查防火墙
sudo iptables -L -n | grep 30001
```

### 视频无法播放

```bash
# 检查编码格式
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 rtsp://10.21.31.103:8554/video1

# 检查 FFmpeg 编解码器
ffmpeg -codecs | grep -E 'h264|hevc'
```

---

## 禁止操作

以下操作在未获得书面放行前禁止执行：

- ❌ 发送心跳以外的控制报文
- ❌ 发送 1003/1 导航下发命令
- ❌ 发送 1004/1 取消命令
- ❌ 发送运动控制命令（Type=2, Cmd=21/22/23/24/25）
- ❌ 修改 AOS/NOS 系统服务
- ❌ 复制地图到其他场地
