#!/usr/bin/env bash
# Simplified rollback script
set -euo pipefail

TARGET_ROOT="$HOME/m20-patrol-robot"
SERVICE_NAME='m20-patrol-readonly.service'

echo "=== 回滚部署 ==="

# 停止服务
systemctl --user stop "$SERVICE_NAME" 2>/dev/null || true
systemctl --user disable "$SERVICE_NAME" 2>/dev/null || true

# 清理部署目录
echo "清理: $TARGET_ROOT"
rm -rf "$TARGET_ROOT"

# 清理服务文件
rm -f "$HOME/.config/systemd/user/$SERVICE_NAME"
systemctl --user daemon-reload

echo "回滚完成 ✅"
echo "请重新解压部署包并运行: bash deploy/scripts/deploy-readonly.sh --one-shot"
