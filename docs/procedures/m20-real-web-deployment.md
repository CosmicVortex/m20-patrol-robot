# M20 Pro 真实 Web 只读部署说明

## 重要边界

本包是 M20 Pro / GOS 的**只读遥测联调包**。默认：

```text
M20_RUNTIME_MODE=realtime_readonly
M20_READ_ONLY_MODE=true
M20_CONTROL_ENABLED=false
M20_TELEMETRY_TX_ENABLED=false
```

不会发送运动、导航、定位重置、充电、云台或巡检任务指令。

当前 Web 页面中的四路视频和奔驰 4S 店地图仍是验收占位，不能在没有现场证据时显示在线视频、真实地图、路线、点位或告警。

## 需要现场确认的前置条件

在 GOS 执行：

```bash
hostname
id
uname -a
python3.8 --version
ip -4 addr
ip route
command -v ffprobe || true
systemctl --user show-environment
nc -zvw3 10.21.31.103 30001
nc -zvw3 10.21.31.103 8554
```

必须确认：

- GOS 地址为 `10.21.31.104`
- AOS 地址为 `10.21.31.103`
- NOS 地址为 `13.21.31.106`
- Python 为 `3.8.10`
- GOS 用户级 systemd 可用
- AOS TCP 30001 可达
- RTSP 8554 是否可达
- 实机软件/固件版本和协议服务版本

如果任一项不满足，不执行安装，先返回完整原始输出。

## 传输到 GOS

将 ZIP 传到 GOS 用户目录，例如：

```bash
scp m20-patrol-robot-deploy.zip <gos-user>@10.21.31.104:/tmp/
ssh <gos-user>@10.21.31.104
cd /tmp
unzip m20-patrol-robot-deploy.zip
cd m20-patrol-robot
```

如果 GOS 没有 `unzip`：

```bash
python3 /path/to/python-unzip.py m20-patrol-robot-deploy.zip
```

不要把 `python-unzip.py` 复制到系统目录。它应与 ZIP 放在同一目录。

## 解包后验证

```bash
sha256sum deploy/readonly-manifest.json
cat deploy/manifest.sha256 2>/dev/null || true
python3.8 -m compileall -q backend
PYTHONPATH=. python3.8 -m pytest -q
```

如果 GOS 没有 pytest，不能把编译通过当成完整测试通过。保留实际输出并标记为未完成。

## 管理员初始化

部署前设置一次临时环境变量，不要把密码写进 Git、ZIP、命令历史或日志：

```bash
export M20_ADMIN_PASSWORD='现场负责人设置的至少12位密码'
```

服务首次启动时，如果数据库中没有 `admin`，会创建管理员账户。启动后建议从 shell 清除：

```bash
unset M20_ADMIN_PASSWORD
```

如果不设置，服务不会自动创建已知默认密码账户。

## 推荐的一键只读部署

先执行无写入预检：

```bash
bash deploy/scripts/deploy-readonly.sh --dry-run
```

确认输出包含：

```text
DRY_RUN=true
NO_FILES_WRITTEN=true
NO_SYSTEMD_CHANGE=true
NO_NETWORK_SIDE_EFFECT=true
```

再执行目标主机预检：

```bash
bash deploy/scripts/deploy-readonly.sh --preflight
```

必须返回：

```text
PY38_RUNTIME_CHECK=PASS
TARGET_IDENTITY_CONFIRMED=PASS
TELEMETRY_TX_ENABLED=false
CONTROL_ENABLED=false
WEB_REALTIME_ENABLED=true
PREFLIGHT=PASS
```

最后执行一键安装、启动和严格健康检查：

```bash
export M20_ADMIN_PASSWORD='现场负责人设置的至少12位密码'
bash deploy/scripts/deploy-readonly.sh --one-shot
unset M20_ADMIN_PASSWORD
```

`--one-shot` 只有在健康检查确认真实数据时才成功。健康门禁要求：

```text
runtime_mode=realtime_readonly
source=REAL
connected=true
valid_frames>0
bytes_received>0
frame_valid=true
message_parsed=true
status_accepted=true
telemetry_fresh=true
data_state=REAL_FRESH
age_ms < stale_after_seconds*1000
control_enabled=false
telemetry_tx_enabled=false
```

如果没有真实遥测，命令应失败。这是预期的安全行为，不要绕过。

## 访问 Web

```text
http://10.21.31.104:8080/
```

笔记本无法直接访问时使用 SSH 隧道：

```bash
ssh -L 8080:10.21.31.104:8080 <gos-user>@10.21.31.104
```

然后浏览器打开：

```text
http://127.0.0.1:8080/
```

## 验证接口

```bash
curl -i http://10.21.31.104:8080/api/v1/health
curl -i http://10.21.31.104:8080/api/v1/status/latest
systemctl --user status m20-patrol-readonly.service --no-pager
journalctl --user -u m20-patrol-readonly.service -n 200 --no-pager
```

首页和状态 API 可以返回，但只有 `source=REAL` 且数据新鲜时，才可以记录为 `runtime_integrated`。

## 视频现状

当前正式文档中的 `video1`、`video2` 只能作为候选文档事实，不能直接视为现场事实。视频放行前需要现场输出：

```bash
ffprobe -hide_banner -rtsp_transport tcp rtsp://10.21.31.103:8554/video1
ffprobe -hide_banner -rtsp_transport tcp rtsp://10.21.31.103:8554/video2
```

执行前确认地址、鉴权和安全范围。不要把用户名、密码或临时令牌写入前端、Git 或报告。

当前页面没有真实 `<video>` 播放、截图或录像成功声明。只有服务端代理、首帧和浏览器可播放证据齐全后，才可实现这些功能。

## 地图现状

当前没有东莞中升奔驰现场地图图片、地图包、地图 ID、坐标系和标定证据。不要使用参考截图、机器狗图片或测试场地地图代替现场地图。

地图导入至少需要：

- 现场地图原始文件
- 地图 ID
- 坐标系和单位
- 与 M20 Pro 当前地图的对应关系
- SHA-256
- 点位和路线标定记录
- 负责人确认

## 日志和回滚

查看服务：

```bash
systemctl --user status m20-patrol-readonly.service --no-pager
journalctl --user -u m20-patrol-readonly.service -n 200 --no-pager
```

停止服务：

```bash
systemctl --user stop m20-patrol-readonly.service
```

回滚到已存在的固定 commit：

```bash
bash deploy/scripts/deploy-readonly.sh --rollback <previous-full-40-char-commit-sha>
```

不要使用当前 dirty 工作树部署，不要使用短 SHA，不要 force push，不要手工绕过 preflight。

## 当前禁止操作

在负责人单独授权、安全快照、急停验证、定位/避障确认和现场放行前，禁止：

- `POST /api/v1/navigation/tasks`
- 导航取消
- 运动状态、步态、速度命令
- 定位重置
- 充电控制
- 云台控制
- 任意高频控制报文

## 现场反馈格式

请返回以下完整输出和执行时间：

```text
[HOST]
hostname/id/uname/python/ip/route

[NETWORK]
AOS 30001/8554 probe

[PREFLIGHT]
deploy-readonly.sh --preflight

[SERVICE]
systemctl status
journalctl

[HEALTH]
curl /api/v1/health
curl /api/v1/status/latest

[MEDIA]
ffprobe 原始输出

[MAP]
现场地图文件名、SHA-256、地图ID、坐标系、负责人确认
```

没有这些现场输出，不能把本包标记为真机部署完成。
