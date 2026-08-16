#!/usr/bin/env bash
# M20 Pro GOS 离线 FFmpeg 安装器
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARCHIVE="$SCRIPT_DIR/ffmpeg-n7.1-latest-linuxarm64-gpl-7.1.tar.xz"
EXPECTED_ARCH="aarch64"
INSTALL_ROOT="${HOME}/.local/opt/m20-ffmpeg/7.1"
BIN_DIR="${HOME}/.local/bin"

fail() { echo "错误: $*" >&2; exit 1; }

[ "$(id -u)" -ne 0 ] || fail "禁止使用 root 用户运行，请使用 GOS 普通用户执行。"
[ -f "$ARCHIVE" ] || fail "离线 FFmpeg 压缩包不存在: $ARCHIVE"

machine_arch="$(uname -m)"
case "$machine_arch" in
  "$EXPECTED_ARCH"|arm64) ;;
  *) fail "架构不匹配：检测到 $machine_arch，需要 aarch64/arm64。" ;;
esac

if command -v sha256sum >/dev/null 2>&1; then
  (cd "$SCRIPT_DIR" && sha256sum -c SHA256SUMS --status) || fail "FFmpeg 压缩包 SHA-256 校验失败。"
else
  fail "系统缺少 sha256sum，无法执行完整性校验。"
fi

mkdir -p "$INSTALL_ROOT" "$BIN_DIR"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

tar -xJf "$ARCHIVE" -C "$tmp_dir"
mapfile -t source_dirs < <(find "$tmp_dir" -mindepth 1 -maxdepth 1 -type d -print)
[ "${#source_dirs[@]}" -eq 1 ] || fail "FFmpeg 压缩包顶层目录数量异常。"
source_dir="${source_dirs[0]}"
[ -x "$source_dir/bin/ffmpeg" ] || fail "压缩包内未找到可执行的 ffmpeg。"
[ -x "$source_dir/bin/ffprobe" ] || fail "压缩包内未找到可执行的 ffprobe。"

rm -rf "$INSTALL_ROOT/current"
mkdir -p "$INSTALL_ROOT/current"
cp -a "$source_dir/bin" "$INSTALL_ROOT/current/"
cp -a "$source_dir/presets" "$INSTALL_ROOT/current/" 2>/dev/null || true
ln -sfn "$INSTALL_ROOT/current/bin/ffmpeg" "$BIN_DIR/ffmpeg"
ln -sfn "$INSTALL_ROOT/current/bin/ffprobe" "$BIN_DIR/ffprobe"
chmod 755 "$INSTALL_ROOT/current/bin/ffmpeg" "$INSTALL_ROOT/current/bin/ffprobe"

"$BIN_DIR/ffmpeg" -version | sed -n '1,2p'
"$BIN_DIR/ffprobe" -version | sed -n '1,2p'
"$BIN_DIR/ffmpeg" -hide_banner -encoders 2>/dev/null | grep -E 'libx264|h264' | head -5 || true

echo "FFmpeg 离线安装完成。"
echo "ffmpeg: $BIN_DIR/ffmpeg"
echo "ffprobe: $BIN_DIR/ffprobe"
echo "请确保 M20 systemd 服务的 PATH 包含 $BIN_DIR。"
