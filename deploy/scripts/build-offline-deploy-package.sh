#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${1:-$ROOT/deploy/m20-patrol-robot-offline-deploy.tar.gz}"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$STAGE/m20-patrol-robot"
(cd "$ROOT" && tar cf - \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='deploy/*.tar.gz' \
  --exclude='deploy/*.tar.gz.sha256' \
  .) | (cd "$STAGE/m20-patrol-robot" && tar xf -)
mkdir -p "$STAGE/m20-patrol-robot/deploy/offline/ffmpeg"
cp "$ROOT/deploy/offline/ffmpeg/ffmpeg-n7.1-latest-linuxarm64-gpl-7.1.tar.xz" \
   "$ROOT/deploy/offline/ffmpeg/SHA256SUMS" \
   "$ROOT/deploy/offline/ffmpeg/install-ffmpeg-offline.sh" \
   "$ROOT/deploy/offline/ffmpeg/OFFLINE_FFMPEG_INSTALL.md" \
   "$STAGE/m20-patrol-robot/deploy/offline/ffmpeg/"

mkdir -p "$(dirname "$OUT")"
tar czf "$OUT" -C "$STAGE" m20-patrol-robot
sha256sum "$OUT" > "${OUT}.sha256"
printf '离线部署包: %s\n包SHA-256: %s\n' "$OUT" "${OUT}.sha256"
