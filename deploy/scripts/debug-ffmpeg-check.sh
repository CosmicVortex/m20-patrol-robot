#!/usr/bin/env bash
# FFmpeg RTSP 检测调试脚本
# 请在 GOS 主机上执行：bash debug-ffmpeg-check.sh

echo "=== FFmpeg 检测调试 ==="
echo ""

# 测试的 ffmpeg 路径
candidates=(
    "/usr/bin/ffmpeg"
    "$HOME/.local/bin/ffmpeg"
    "/opt/m20-ffmpeg/bin/ffmpeg"
)

for candidate in "${candidates[@]}"; do
    echo "候选: $candidate"
    if [ ! -x "$candidate" ]; then
        echo "  跳过: 文件不存在或不可执行"
        continue
    fi
    
    echo "  版本:"
    "$candidate" -version 2>/dev/null | head -1
    
    echo "  检查 RTSP demuxer..."
    # 方法1: tr + grep -qx
    if "$candidate" -hide_banner -demuxers 2>/dev/null | tr -s ' \t\n' '\n' | grep -qx rtsp; then
        echo "    tr+grep-qx: ✅ 找到 rtsp"
    else
        echo "    tr+grep-qx: ❌ 未找到 rtsp"
    fi
    
    # 方法2: 直接输出原始数据供分析
    echo "  原始 demuxers 输出（前20行）:"
    "$candidate" -hide_banner -demuxers 2>/dev/null | head -20 | cat -v
    
    echo "  查找包含 rtsp 的行:"
    "$candidate" -hide_banner -demuxers 2>/dev/null | grep -i rtsp | cat -v || echo "    无匹配"
    
    echo ""
done

echo "=== 环境信息 ==="
echo "grep 版本: $(grep --version 2>&1 | head -1)"
echo "tr 版本: $(tr --version 2>&1 | head -1 || echo 'unknown')"
echo "系统: $(uname -a)"
