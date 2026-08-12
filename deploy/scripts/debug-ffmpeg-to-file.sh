#!/usr/bin/env bash
# FFmpeg 检测调试脚本 - 输出到文件版本
# 请在 GOS 主机上执行：bash debug-ffmpeg-to-file.sh

LOG="/tmp/ffmpeg-debug.log"
echo "=== FFmpeg 检测调试 $(date) ===" > "$LOG"
echo "" >> "$LOG"

# 环境信息
echo "[环境信息]" >> "$LOG"
echo "  PATH=$PATH" >> "$LOG"
echo "  hostname=$(hostname)" >> "$LOG"
echo "  uname=$(uname -a)" >> "$LOG"
echo "  grep version: $(grep --version 2>&1 | head -1)" >> "$LOG"
echo "  tr version: $(tr --version 2>&1 | head -1 2>/dev/null || echo 'unknown')" >> "$LOG"
echo "" >> "$LOG"

# 候选路径
candidates=(
    "/usr/bin/ffmpeg"
    "$HOME/.local/bin/ffmpeg"
    "/opt/m20-ffmpeg/bin/ffmpeg"
)

for candidate in "${candidates[@]}"; do
    echo "[候选: $candidate]" >> "$LOG"
    
    # 检查是否存在
    if [ ! -e "$candidate" ]; then
        echo "  状态: 文件不存在" >> "$LOG"
        echo "" >> "$LOG"
        continue
    fi
    
    if [ ! -x "$candidate" ]; then
        echo "  状态: 存在但不可执行" >> "$LOG"
        ls -la "$candidate" >> "$LOG" 2>&1
        echo "" >> "$LOG"
        continue
    fi
    
    echo "  状态: 存在且可执行" >> "$LOG"
    ls -la "$candidate" >> "$LOG" 2>&1
    echo "  版本:" >> "$LOG"
    "$candidate" -version 2>&1 | head -1 >> "$LOG"
    
    # 检查 RTSP demuxer
    echo "  RTSP demuxer 检查:" >> "$LOG"
    
    # 保存输出到临时文件
    DEMUX_FILE="/tmp/demuxers_$(basename "$candidate").txt"
    "$candidate" -hide_banner -demuxers > "$DEMUX_FILE" 2>/dev/null
    
    echo "    原始输出前30行:" >> "$LOG"
    head -30 "$DEMUX_FILE" >> "$LOG"
    
    echo "    包含 rtsp 的行:" >> "$LOG"
    grep -i rtsp "$DEMUX_FILE" >> "$LOG" || echo "    (无匹配)" >> "$LOG"
    
    # 方法测试
    echo "    检测方法测试结果:" >> "$LOG"
    
    # 方法1: tr + grep -qx
    if tr -s ' \t\n' '\n' < "$DEMUX_FILE" | grep -qx rtsp 2>/dev/null; then
        echo "      tr+grep-qx: ✅ 找到" >> "$LOG"
    else
        echo "      tr+grep-qx: ❌ 未找到" >> "$LOG"
    fi
    
    # 方法2: awk 提取第二列
    if awk '{print $2}' "$DEMUX_FILE" | grep -qx rtsp 2>/dev/null; then
        echo "      awk+grep-qx: ✅ 找到" >> "$LOG"
    else
        echo "      awk+grep-qx: ❌ 未找到" >> "$LOG"
    fi
    
    # 方法3: grep -w
    if grep -qw rtsp "$DEMUX_FILE" 2>/dev/null; then
        echo "      grep-qw: ✅ 找到" >> "$LOG"
    else
        echo "      grep-qw: ❌ 未找到" >> "$LOG"
    fi
    
    echo "" >> "$LOG"
done

echo "=== 完成 ===" >> "$LOG"
echo "调试日志已保存到: $LOG"
