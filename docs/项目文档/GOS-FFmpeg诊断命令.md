# GOS FFmpeg 诊断命令（请在 GOS 主机上执行）

# 1. 检查所有 ffmpeg 位置及版本
echo "=== 所有ffmpeg位置 ==="
which -a ffmpeg || true
command -v ffmpeg || true
ls -la /usr/bin/ffmpeg ~/.local/bin/ffmpeg /usr/local/bin/ffmpeg 2>/dev/null || true

echo ""
echo "=== 各版本ffmpeg ==="
/usr/bin/ffmpeg -version 2>/dev/null | head -1 || true
~/.local/bin/ffmpeg -version 2>/dev/null | head -1 || true
/usr/local/bin/ffmpeg -version 2>/dev/null | head -1 || true

echo ""
echo "=== PATH顺序 ==="
echo $PATH

echo ""
echo "=== RTSP支持检查 ==="
echo "系统ffmpeg:"
/usr/bin/ffmpeg -hide_banner -demuxers 2>/dev/null | grep rtsp || echo "无rtsp demuxer"
echo "离线ffmpeg:"
~/.local/bin/ffmpeg -hide_banner -demuxers 2>/dev/null | grep rtsp || echo "无rtsp demuxer或路径不存在"

echo ""
echo "=== 离线安装目录 ==="
ls -la ~/.local/opt/m20-ffmpeg/ 2>/dev/null || echo "离线安装目录不存在"
ls -la ~/.local/bin/ffmpeg 2>/dev/null || echo "~/.local/bin/ffmpeg不存在"
