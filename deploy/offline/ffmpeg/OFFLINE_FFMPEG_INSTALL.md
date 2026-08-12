# M20 Pro GOS 离线 FFmpeg 安装包

## 1. 结论

当前云端开发机已安装：

```text
ffmpeg 7:7.1.5-0+deb13u1
ffprobe 7.1.5
主机架构：amd64
```

但这不能证明机器狗 GOS 主机已经安装 FFmpeg。云端无法直接访问 GOS，必须在 GOS 主机执行本说明中的检查命令。

项目浏览器视频播放链路需要：

- `ffmpeg`：RTSP 转码为浏览器可读取的 fragmented MP4；
- `ffprobe`：RTSP 地址、编码、分辨率和帧率探测；
- 不需要 `dumped`、GStreamer、MediaMTX、VLC 或其他媒体服务器。

GOS 项目资料标注为 Ubuntu 20.04.6 LTS、aarch64、Python 3.8.10，因此本离线包按 **Linux aarch64/arm64** 构建。不能将云端 amd64 的 FFmpeg 二进制直接传到 GOS。

## 2. 所需版本

本包使用 FFmpeg 7.1 GPL aarch64 静态构建：

```text
文件：ffmpeg-n7.1-latest-linuxarm64-gpl-7.1.tar.xz
架构：aarch64 / arm64
版本系列：FFmpeg 7.1
构建类型：静态构建，避免 GOS 离线环境缺少共享库
必需命令：ffmpeg、ffprobe
```

该版本满足当前代码使用的能力：

- RTSP 输入；
- TCP 传输；
- `-rw_timeout`；
- H.264 输入/输出；
- `libx264` 编码；
- fragmented MP4 输出；
- `ffprobe -show_entries stream=codec_name,width,height,r_frame_rate`。

如果现场确认 GOS 实际架构不是 aarch64，禁止安装本包。先返回：

```bash
uname -m
```

## 3. 离线包内容

本目录应包含：

```text
ffmpeg-n7.1-latest-linuxarm64-gpl-7.1.tar.xz
SHA256SUMS
install-ffmpeg-offline.sh
OFFLINE_FFMPEG_INSTALL.md
```

校验包文件：

```bash
sha256sum -c SHA256SUMS
```

必须显示：

```text
...: OK
```

## 4. 传输到 GOS

在联网的准备机上，先取得本目录的完整文件。通过 MobaXterm SFTP、U 盘或其他经批准的离线介质，将整个目录传到 GOS，例如：

```text
/home/<现场用户>/m20-ffmpeg-offline/
```

传输后目录结构必须保持不变。

## 5. GOS 安装步骤

### 5.1 先确认当前是否已安装

```bash
uname -m
command -v ffmpeg || true
command -v ffprobe || true
ffmpeg -version 2>/dev/null | sed -n '1,2p' || true
ffprobe -version 2>/dev/null | sed -n '1,2p' || true
```

判定规则：

- `uname -m` 必须为 `aarch64` 或 `arm64`；
- `ffmpeg` 和 `ffprobe` 均能执行；
- 版本建议为 7.1 或更高；
- 必须验证编码器：

```bash
ffmpeg -hide_banner -encoders 2>/dev/null | grep -E 'libx264|h264'
```

如果已有满足条件的 FFmpeg，无需重复安装，但仍需执行第 7 节验证。

### 5.2 执行离线安装

```bash
cd /home/<现场用户>/m20-ffmpeg-offline
chmod +x install-ffmpeg-offline.sh
sha256sum -c SHA256SUMS
./install-ffmpeg-offline.sh
```

安装器不使用网络、不调用 apt、不创建 Python 虚拟环境、不需要 dumped。

安装位置：

```text
~/.local/opt/m20-ffmpeg/7.1/current/bin/ffmpeg
~/.local/opt/m20-ffmpeg/7.1/current/bin/ffprobe
~/.local/bin/ffmpeg
~/.local/bin/ffprobe
```

## 6. 让 systemd 服务找到 FFmpeg

当前项目服务使用 `/usr/bin/python3` 启动。由于安装器默认使用用户目录，必须把 FFmpeg 目录加入 systemd 的 `PATH`。

编辑用户服务：

```bash
systemctl --user edit m20-patrol-readonly.service
```

加入：

```ini
[Service]
Environment=PATH=%h/.local/bin:/usr/local/bin:/usr/bin:/bin
```

然后执行：

```bash
systemctl --user daemon-reload
systemctl --user restart m20-patrol-readonly.service
```

验证服务环境：

```bash
systemctl --user show m20-patrol-readonly.service -p Environment
journalctl --user -u m20-patrol-readonly.service -n 80 --no-pager
```

也可以在服务文件的 `[Service]` 段直接加入上述 `Environment=PATH=...`，再重新运行部署脚本。不要依赖交互式 shell 的 `.bashrc`，systemd 不一定读取它。

## 7. FFmpeg 功能验证

### 7.1 基础验证

```bash
~/.local/bin/ffmpeg -version
~/.local/bin/ffprobe -version
~/.local/bin/ffmpeg -hide_banner -encoders | grep -E 'libx264|h264'
~/.local/bin/ffmpeg -hide_banner -protocols | grep -w rtsp
```

### 7.2 四路 RTSP 探测

以下地址必须由现场负责人确认后使用。地址不可达不等于 FFmpeg 安装失败。

```bash
ffprobe -v error -rtsp_transport tcp \
  -show_entries stream=codec_name,width,height,r_frame_rate \
  -of json 'rtsp://10.21.31.103:8554/video1'

ffprobe -v error -rtsp_transport tcp \
  -show_entries stream=codec_name,width,height,r_frame_rate \
  -of json 'rtsp://10.21.31.103:8554/video2'

ffprobe -v error -rtsp_transport tcp \
  -show_entries stream=codec_name,width,height,r_frame_rate \
  -of json 'rtsp://<现场云台地址>:554/id=1&type=0'

ffprobe -v error -rtsp_transport tcp \
  -show_entries stream=codec_name,width,height,r_frame_rate \
  -of json 'rtsp://<现场确认地址>:<端口>/<路径>'
```

注意：云台地址、端口和第四路地址在没有现场输出前只能标记为候选值，不能当作已确认事实。

### 7.3 浏览器接口验证

服务启动后，在 GOS 本机执行：

```bash
curl -i http://127.0.0.1:8080/api/v1/video
```

登录获取 Cookie 后，再请求播放接口。播放接口需要认证 Cookie；不能直接用匿名请求判断播放链路。

```bash
curl -i -c /tmp/m20-cookie.txt \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"123456"}' \
  http://127.0.0.1:8080/api/v1/auth/login

curl --max-time 20 -v -b /tmp/m20-cookie.txt \
  'http://127.0.0.1:8080/api/v1/video/playback/front' \
  -o /tmp/m20-front.mp4
```

预期：

- HTTP 状态为 200，或 RTSP 不可达时在日志中明确记录失败；
- `Content-Type: video/mp4`；
- `/tmp/m20-front.mp4` 能看到 MP4 fragmented 文件头或持续增长；
- 浏览器访问 `http://10.21.31.104:8080/` 后，登录并启动视频，能获得首帧。

## 8. 服务验证

```bash
systemctl --user status m20-patrol-readonly.service --no-pager
curl --fail --silent --show-error http://127.0.0.1:8080/api/v1/health
curl --fail --silent --show-error http://127.0.0.1:8080/api/v1/status/latest
journalctl --user -u m20-patrol-readonly.service --since '-5 min' --no-pager
```

只读模式必须保持：

```text
runtime_mode=realtime_readonly
read_only_mode=true
control_enabled=false
telemetry_tx_enabled=false
```

## 9. 回滚/卸载

停止服务：

```bash
systemctl --user stop m20-patrol-readonly.service
```

删除本次用户级 FFmpeg：

```bash
rm -f ~/.local/bin/ffmpeg ~/.local/bin/ffprobe
rm -rf ~/.local/opt/m20-ffmpeg/7.1
systemctl --user daemon-reload
```

如果原系统已有 `/usr/bin/ffmpeg`，不要删除或覆盖它。只删除本次安装器创建的用户目录和符号链接。

## 10. 故障排查

### `Exec format error`

架构不匹配。执行：

```bash
uname -m
```

aarch64 GOS 不能使用 amd64/x86_64 FFmpeg。

### `ffmpeg: command not found`

检查：

```bash
ls -l ~/.local/bin/ffmpeg
systemctl --user show m20-patrol-readonly.service -p Environment
```

确认 systemd 的 PATH 包含 `%h/.local/bin`。

### `No such file or directory` 或缺少共享库

本包是静态构建，通常不应出现共享库缺失。若出现，记录完整输出并停止现场修改，不要联网临时安装未知库。

### `Unknown encoder 'libx264'`

当前播放实现需要 `libx264`。确认安装包未被替换，并执行：

```bash
~/.local/bin/ffmpeg -hide_banner -encoders | grep libx264
```

### RTSP 连接失败

先区分软件和网络：

```bash
nc -vz 10.21.31.103 8554
nc -vz <现场云台地址> 554
```

`nc` 不存在时可使用现场已有 TCP 检查工具。不要因为 RTSP 不通而重复安装 FFmpeg；需要检查地址、端口、网线、AOS/云台服务和防火墙。

### 页面显示 BLOCKED/UNVERIFIED

检查：

```bash
curl -s http://127.0.0.1:8080/api/v1/video
journalctl --user -u m20-patrol-readonly.service -n 100 --no-pager
```

确认 `allow_real_io=true`、RTSP 地址已配置，并重新启动服务。

## 11. 现场证据要求

以下证据全部取得前，状态只能写为 `offline_verified` 或 `runtime_integrated`，不能写为 `field_verified`：

- GOS `uname -m` 和 `python3 --version`；
- GOS `ffmpeg -version` 和 `ffprobe -version`；
- 四路 RTSP `ffprobe` 输出；
- Web 播放接口 HTTP 头和首帧文件；
- 浏览器真实播放截图或录屏；
- 页面关闭/服务停止后的进程检查：

```bash
pgrep -af ffmpeg || true
systemctl --user stop m20-patrol-readonly.service
sleep 2
pgrep -af ffmpeg || true
```

本离线包和本说明只证明安装材料已经准备，不证明 GOS 已安装或视频已现场可用。
