#!/bin/bash
# M20 Pro 快速部署脚本 - 单步部署
# 用法: bash one-shot-deploy.sh
# 说明: 自动完成预检查、安装、启动、验证全流程

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "========================================"
echo "  M20 Pro 快速部署"
echo "========================================"
echo ""

# 检查是否在正确的目录
if [ ! -f "$ROOT/deploy/readonly-manifest.json" ]; then
    echo "错误: 请在 m20-patrol-robot 目录下执行此脚本" >&2
    echo "当前目录: $(pwd)" >&2
    echo "期望目录: $ROOT" >&2
    exit 1
fi

echo "[1/3] 执行预检查和部署..."
bash "$ROOT/deploy/scripts/deploy-readonly.sh" --one-shot

echo ""
echo "[2/3] 等待服务启动..."
sleep 3

echo ""
echo "[3/3] 验证服务状态..."
if systemctl --user is-active m20-patrol-readonly.service &>/dev/null; then
    echo "  ✓ 服务已启动"
else
    echo "  ✗ 服务启动失败"
    echo ""
    echo "查看日志:"
    echo "  journalctl --user -u m20-patrol-readonly -n 20 --no-pager"
    exit 1
fi

echo ""
echo "========================================"
echo "  部署成功!"
echo "========================================"
echo ""
echo "访问地址:"
echo "  GOS本机:   http://localhost:8080/"
echo "  笔记本:    http://10.21.31.104:8080/"
echo ""
echo "常用命令:"
echo "  查看状态:  systemctl --user status m20-patrol-readonly"
echo "  查看日志:  journalctl --user -u m20-patrol-readonly -f"
echo "  停止服务:  systemctl --user stop m20-patrol-readonly"
echo "  启动服务:  systemctl --user start m20-patrol-readonly"
echo ""
