# FFmpeg 离线安装指南

## ⚠️ 重要说明

由于 FFmpeg 官方已不再提供预编译的 arm64 静态构建包，**必须在 GOS 主机上编译安装**。

## 安装步骤（在GOS主机上执行）

### 方案一：源码编译安装（推荐）

```bash
# 进入FFmpeg目录
cd ~/m20-patrol-robot/deploy/offline/ffmpeg

# 执行编译安装脚本
bash compile-ffmpeg-arm64.sh
```

编译脚本会自动：
1. 安装编译依赖
2. 克隆 FFmpeg 7.1 源码
3. 配置并编译（启用RTSP、H.264等）
4. 打包为 `ffmpeg-n7.1-latest-linuxarm64-gpl-7.1.tar.xz`

### 方案二：使用包管理器（较快）

```bash
# 在GOS主机上安装FFmpeg
sudo apt-get update
sudo apt-get install -y ffmpeg

# 验证版本（需要≥7.1）
ffmpeg -version | head -1

# 创建符号链接到项目目录
mkdir -p ~/m20-patrol-robot/deploy/offline/ffmpeg
ln -sf /usr/bin/ffmpeg ~/m20-patrol-robot/deploy/offline/ffmpeg/
ln -sf /usr/bin/ffprobe ~/m20-patrol-robot/deploy/offline/ffmpeg/
```

## 验证安装

```bash
# 检查版本
ffmpeg -version

# 检查RTSP支持
ffmpeg -protocols 2>/dev/null | grep rtsp

# 检查H.264编码器支持
ffmpeg -hide_banner -encoders 2>/dev/null | grep h264
```

## 部署到GOS

安装完成后，执行：

```bash
cd ~/m20-patrol-robot
bash deploy/scripts/deploy-readonly.sh --one-shot
```

## 要求

- FFmpeg 版本 ≥ 7.1
- 支持 RTSP over TCP
- 架构：aarch64/arm64
- 需要编译工具链（方案一）或apt源（方案二）
