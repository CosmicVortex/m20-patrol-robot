# M20 Pro 部署与接入准备说明

**适用范围：** M20 Pro 第一阶段的离线协议模块、模拟仪表盘，以及后续真实状态和视频接入准备。
**文件依据：** 《软件开发指南》V1.2.1（2026-05-18）和现场只读核验结果。

## 1. 部署原则

业务程序部署在 **GOS**，不部署到 AOS 或 NOS。

- AOS 负责运动控制和 `basic_server`；不安装业务程序、不修改原厂服务。
- NOS 负责建图、定位和导航；不部署 Web、转码或 AI 业务，不修改原始地图。
- GOS 用于后续状态聚合、视频网关、地图副本展示和 Web 服务。
- 使用现场批准的非 root 账户。
- 固定 Git commit 部署；凭据、地图、视频和本地配置不得提交 Git。

当前仓库没有可部署的机器人 TCP 客户端、RTSP 转码服务或导航控制服务。当前仪表盘仅显示模拟数据。

## 2. 当前实现边界

已实现并完成离线测试：

- 16 字节 APDU 离线编解码；
- JSON/XML `PatrolDevice` 通用 ASDU 编解码；
- TCP 拆包、粘包和截断帧的离线解析；
- 回环地址上的模拟只读仪表盘。

当前仪表盘固定输出：

```json
{
  "source": "SIMULATED",
  "connected": false,
  "control_enabled": false,
  "navigation": "NOT_CONNECTED"
}
```

不得将该页面称为真实状态、实时视频或巡逻控制页面。

## 3. GOS 部署前核验

在获准登录的 GOS 上执行以下只读命令，并保存完整输出：

```bash
mkdir -p ~/m20-readonly-feedback
OUT=~/m20-readonly-feedback/gos-readiness-$(date +%F-%H%M%S).txt
{
  echo '===== IDENTITY ====='
  hostname
  id
  uname -a
  cat /etc/os-release 2>/dev/null || true

  echo '===== RESOURCES ====='
  lscpu 2>/dev/null || true
  free -h 2>/dev/null || true
  df -h 2>/dev/null || true

  echo '===== NETWORK ====='
  ip -br addr 2>/dev/null || true
  ip route 2>/dev/null || true

  echo '===== VIDEO RUNTIMES ====='
  command -v ffmpeg || true
  command -v ffprobe || true
  command -v gst-launch-1.0 || true
  ffmpeg -version 2>/dev/null | sed -n '1,8p' || true
  gst-inspect-1.0 2>/dev/null | grep -Ei 'mpp|rockchip|webrtc|rtsp|h264|h265' | sed -n '1,120p' || true

  echo '===== LOCAL PORTS ====='
  ss -lntup 2>/dev/null || true
  echo '===== END ====='
} | tee "$OUT"
printf 'OUTPUT=%s\n' "$OUT"
```

发送前遮盖密码、私钥、Token、Cookie、Wi-Fi 密钥、VPN 凭据、用户名、MAC 地址、设备序列号、完整公网 IP、默认网关、DNS 搜索域和客户数据。

## 4. 固定版本部署

以下命令中的仓库地址和提交 SHA 必须替换为现场批准值。未确认的值不得执行。

```bash
mkdir -p ~/src
cd ~/src
git clone <PRIVATE_REPOSITORY_URL> m20-patrol-robot
cd m20-patrol-robot
git fetch --all --tags
git checkout <APPROVED_COMMIT_SHA>
git status --short --branch
git rev-parse HEAD
```

验收条件：工作区没有未预期变更，`HEAD` 与批准的提交 SHA 一致。

创建虚拟环境并运行离线测试：

```bash
cd ~/src/m20-patrol-robot
python3 -m venv .venv
. .venv/bin/activate
python -m pip install pytest
PYTHONPATH=. python -m pytest backend/tests -q
python -m compileall -q backend
git diff --check
```

不得使用 `sudo pip` 或系统范围 pip。

## 5. 模拟仪表盘验证

只允许回环访问：

```bash
cd ~/src/m20-patrol-robot
. .venv/bin/activate
PYTHONPATH=. python -c 'from backend.app.dashboard import serve_dashboard; serve_dashboard(host="127.0.0.1", port=8080)'
```

在同一台 GOS 的另一个终端验证：

```bash
curl -i http://127.0.0.1:8080/
curl -i http://127.0.0.1:8080/api/v1/status/latest
```

停止服务时在启动终端按 `Ctrl+C`。当前不得绑定 `0.0.0.0`，不得配置 systemd 自启动或公网访问。

## 6. 真实状态和视频接入前置条件

### 状态

《软件开发指南》V1.2.1 记载：AOS 的候选接口为 TCP `10.21.31.103:30001` 和 UDP `10.21.31.103:30000`。在现场确认主机、固件、权限和协议样本前，程序不得建立连接或发送心跳。

真实状态接入前必须具备：

1. M20 Pro 实际固件版本和兼容性说明；
2. 已确认的 AOS 主机和第三方客户端许可；
3. 真实状态样本及字段解析测试；
4. 断线、过期状态和异常状态处理；
5. 审计、权限和控制隔离设计。

### 视频

官方资料记录前后本体相机候选源为：

```text
rtsp://10.21.31.103:8554/video1
rtsp://10.21.31.103:8554/video2
```

浏览器不能直接依赖 RTSP/H.265。计划是在 GOS 使用共享转码管线输出 WebRTC/H.264，或以 HLS/H.264 作为高延迟备选方案。

实机接入前必须确认：

1. 两路 RTSP 可达；
2. 实际编码、分辨率、帧率和稳定性；
3. GOS 的 FFmpeg/GStreamer 与 RK3588 硬件编解码支持；
4. CPU、内存、温度、延迟与掉线恢复；
5. 视频访问控制与数据留存策略。

不得修改 AOS 的原厂推流脚本。

## 7. Web 控制边界

建图完成、地图可读或模拟仪表盘可访问，都不构成 Web 控制放行条件。

只有在真实状态、定位/保护解析、视频、导航安全门控、单点回归、审计授权和现场书面安全放行全部完成后，才可单独评审 Web 是否增加受控导航能力。默认状态始终是控制关闭。
