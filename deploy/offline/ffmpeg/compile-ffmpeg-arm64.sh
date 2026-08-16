#!/usr/bin/env bash
# M20 Pro GOS FFmpeg 编译安装脚本
# 在GOS主机上执行此脚本，将从源码编译FFmpeg 7.1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_ARCHIVE="$SCRIPT_DIR/ffmpeg-n7.1-latest-linuxarm64-gpl-7.1.tar.xz"
BUILD_DIR="/tmp/ffmpeg-build"
FFMPEG_VERSION="n7.1"

echo "=========================================="
echo " FFmpeg 7.1 ARM64 编译安装"
echo "=========================================="
echo ""

# 检查架构
machine_arch="$(uname -m)"
if [[ "$machine_arch" != "aarch64" && "$machine_arch" != "arm64" ]]; then
    echo "错误：当前架构为 $machine_arch，需要 aarch64/arm64"
    exit 1
fi
echo "✅ 架构检查通过: $machine_arch"

# 安装编译依赖
echo ""
echo "【步骤1】安装编译依赖..."
sudo apt-get update -qq
sudo apt-get install -y \
    build-essential \
    git \
    autoconf \
    automake \
    libtool \
    nasm \
    yasm \
    cmake \
    pkg-config \
    libssl-dev \
    zlib1g-dev \
    libmp3lame-dev \
    libopus-dev \
    libvorbis-dev \
    libvpx-dev \
    libx264-dev \
    libx265-dev \
    libnuma-dev \
    wget \
    tar \
    xz-utils

echo "✅ 依赖安装完成"

# 清理旧构建目录
echo ""
echo "【步骤2】准备构建目录..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# 克隆FFmpeg源码
echo ""
echo "【步骤3】克隆 FFmpeg $FFMPEG_VERSION 源码..."
git clone --depth 1 --branch "$FFMPEG_VERSION" https://git.ffmpeg.org/ffmpeg.git ffmpeg-src
cd ffmpeg-src

# 配置
echo ""
echo "【步骤4】配置 FFmpeg..."
./configure \
    --prefix="$BUILD_DIR/ffmpeg-install" \
    --enable-gpl \
    --enable-nonfree \
    --enable-libmp3lame \
    --enable-libopus \
    --enable-libvorbis \
    --enable-libvpx \
    --enable-libx264 \
    --enable-libx265 \
    --enable-nonfree \
    --arch=arm64 \
    --target-os=linux \
    --enable-static \
    --disable-shared \
    --disable-doc \
    --disable-programs \
    --extra-cflags="-O3 -march=native"

# 编译
echo ""
echo "【步骤5】编译 FFmpeg（这可能需要几分钟）..."
make -j$(nproc)

# 安装
echo ""
echo "【步骤6】安装 FFmpeg..."
make install

# 验证编译结果
echo ""
echo "【步骤7】验证编译结果..."
if [[ ! -x "$BUILD_DIR/ffmpeg-install/bin/ffmpeg" ]]; then
    echo "错误：编译失败，未找到 ffmpeg 可执行文件"
    exit 1
fi

if [[ ! -x "$BUILD_DIR/ffmpeg-install/bin/ffprobe" ]]; then
    echo "错误：编译失败，未找到 ffprobe 可执行文件"
    exit 1
fi

echo "✅ FFmpeg 编译成功"
"$BUILD_DIR/ffmpeg-install/bin/ffmpeg" -version | head -2

# 打包
echo ""
echo "【步骤8】打包 FFmpeg..."
cd "$BUILD_DIR"
tar cJf "$OUTPUT_ARCHIVE" ffmpeg-install/bin/ffmpeg ffmpeg-install/bin/ffprobe

# 计算SHA256
echo ""
echo "【步骤9】计算校验和..."
sha256sum "$OUTPUT_ARCHIVE" > "$SCRIPT_DIR/SHA256SUMS"
echo "SHA256: $(cat "$SCRIPT_DIR/SHA256SUMS")"

# 验证压缩包
echo ""
echo "【步骤10】验证压缩包..."
TEMP_DIR=$(mktemp -d)
tar -xJf "$OUTPUT_ARCHIVE" -C "$TEMP_DIR"
if [[ -x "$TEMP_DIR/bin/ffmpeg" ]]; then
    echo "✅ 压缩包验证通过"
    "$TEMP_DIR/bin/ffmpeg" -version | head -1
else
    echo "❌ 压缩包验证失败"
    rm -rf "$TEMP_DIR"
    exit 1
fi
rm -rf "$TEMP_DIR"

# 清理
echo ""
echo "【步骤11】清理构建文件..."
rm -rf "$BUILD_DIR"

# 最终验证
echo ""
echo "=========================================="
echo " FFmpeg 编译安装完成！"
echo "=========================================="
echo ""
echo "压缩包位置: $OUTPUT_ARCHIVE"
echo "文件大小: $(ls -lh "$OUTPUT_ARCHIVE" | awk '{print $5}')"
echo ""
echo "下一步：运行离线安装脚本"
echo "  bash $SCRIPT_DIR/install-ffmpeg-offline.sh"
echo ""
