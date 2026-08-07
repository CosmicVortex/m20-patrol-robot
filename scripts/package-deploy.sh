#!/usr/bin/env bash
# 创建轻量化部署包
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${1:-${REPO_ROOT}/dist}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "${OUTPUT_DIR}"

cd "${REPO_ROOT}"

# 最小部署包（仅代码和部署脚本）
echo "Creating minimal deployment package..."
tar -czf "${OUTPUT_DIR}/m20-patrol-minimal-${TIMESTAMP}.tar.gz" \
  --exclude='*/__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.md' \
  --exclude='docs/' \
  --exclude='.git/' \
  --exclude='dist/' \
  backend/app/ \
  deploy/scripts/ \
  deploy/systemd/

# 完整部署包（包含文档）
echo "Creating complete deployment package..."
tar -czf "${OUTPUT_DIR}/m20-patrol-complete-${TIMESTAMP}.tar.gz" \
  --exclude='**/__pycache__' \
  --exclude='**/*.pyc' \
  --exclude='.git/' \
  --exclude='dist/' \
  .

# 显示大小
echo ""
echo "Package sizes:"
ls -lh "${OUTPUT_DIR}/m20-patrol-"*.tar.gz

echo ""
echo "Done. Packages in: ${OUTPUT_DIR}"
