# GOS FFmpeg 诊断命令（请在 GOS 主机上执行）

## 快速诊断

```bash
# 1. 检查所有 ffmpeg 位置
which -a ffmpeg
ls -la /usr/bin/ffmpeg ~/.local/bin/ffmpeg /usr/local/bin/ffmpeg 2>/dev/null

# 2. 检查各版本
/usr/bin/ffmpeg -version 2>/dev/null | head -1
~/.local/bin/ffmpeg -version 2>/dev/null | head -1

# 3. 检查RTSP支持
echo "系统ffmpeg RTSP:"
/usr/bin/ffmpeg -hide_banner -demuxers 2>/dev/null | grep rtsp

echo "离线ffmpeg RTSP:"
~/.local/bin/ffmpeg -hide_banner -demuxers 2>/dev/null | grep rtsp || echo "离线ffmpeg不存在"

# 4. 检查PATH
echo $PATH
```

## 问题分析

### 问题1：系统 ffmpeg 不支持 RTSP 传输协议

**现象**：部署脚本报错 "FFmpeg不支持RTSP协议"

**原因**：Ubuntu 20.04 仓库版本的 ffmpeg 4.2.7 编译时禁用了部分协议支持。

**解决方案**：使用离线 FFmpeg 7.1 包。

### 问题2：部署脚本检测逻辑错误

**原逻辑**（错误）：
```bash
FFMPEG_BIN="$(command -v ffmpeg || true)"
if [ -z "$FFMPEG_BIN" ] && [ -x "$HOME/.local/bin/ffmpeg" ]; then
    FFMPEG_BIN="$HOME/.local/bin/ffmpeg"
fi
```

**问题**：`command -v ffmpeg` 找到 `/usr/bin/ffmpeg`，永远不检查离线包。

**修复逻辑**（正确）：
```bash
for _candidate in /usr/bin/ffmpeg "$HOME/.local/bin/ffmpeg" "/opt/m20-ffmpeg/bin/ffmpeg"; do
    [ -x "$_candidate" ] || continue
    if "$_candidate" -hide_banner -demuxers 2>/dev/null | grep -qw rtsp \
       && "$_candidate" -hide_banner -protocols 2>/dev/null | grep -qwE 'tcp|udp'; then
        ffmpeg_bin="$_candidate"
        break
    fi
done
```

### 问题3：正则表达式兼容性问题

**问题**：`grep -qwE '(^|\s)(tcp|udp)(\s|$)'` 在某些 grep 版本中 `\s` 不被识别。

**修复**：简化为 `grep -qwE 'tcp|udp'`，直接匹配关键字。

---

## FFmpeg RTSP 架构说明

FFmpeg 的 RTSP 支持通过以下组件实现：

```
RTSP 应用层协议
    ↓
rtsp demuxer (libavformat)     ← 通过 -demuxers | grep rtsp 检测
    ↓
RTP/RTCP 协议
    ↓
tcp/udp protocol (libavformat)  ← 通过 -protocols | grep -E 'tcp|udp' 检测
    ↓
IP 传输层
```

**注意**：`-protocols` 输出不包含 "rtsp" 字样，因为 RTSP 是应用层协议，底层使用 RTP/TCP/UDP。

---

## 部署步骤（含 FFmpeg 修复）

```bash
# 1. SSH 登录 GOS
ssh user@10.21.31.104

# 2. 传输新部署包（从云端下载链接获取）
# 使用 MobaXterm 文件浏览器拖拽上传

# 3. 解压覆盖
cd ~
tar xzf m20-patrol-robot-offline-deploy.tar.gz -C ~/

# 4. 环境预检
cd ~/m20-patrol-robot
bash deploy/scripts/deploy-readonly.sh --preflight

# 5. 执行部署
bash deploy/scripts/deploy-readonly.sh --one-shot

# 6. 验证服务
systemctl --user status m20-patrol-readonly.service
curl http://127.0.0.1:8080/api/v1/health
```

---

## 关于替换系统 FFmpeg

**不建议直接替换 `/usr/bin/ffmpeg`**，原因：
1. 需要 root 权限修改系统文件
2. Ubuntu 系统包可能依赖特定版本的 FFmpeg
3. 升级后可能被系统包管理器覆盖

**推荐方案**：
- 保持系统 FFmpeg 在 `/usr/bin/ffmpeg`
- 离线 FFmpeg 安装到 `~/.local/bin/ffmpeg`
- 部署脚本自动选择支持 RTSP 的版本
