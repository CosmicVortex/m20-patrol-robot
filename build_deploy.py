#!/usr/bin/env python3
"""构建部署包 - 仅包含必要的Web文件"""
import zipfile, hashlib, os
from pathlib import Path

root = Path('.')
target_files = []

# 收集Web相关文件
web_dir = root / 'docs' / 'website'
if web_dir.exists():
    for f in web_dir.rglob('*'):
        if f.is_file():
            target_files.append(f)

# 收集后端文件
backend_dir = root / 'backend'
if backend_dir.exists():
    for f in backend_dir.rglob('*.py'):
        target_files.append(f)

# 收集部署脚本
deploy_dir = root / 'deploy'
if deploy_dir.exists():
    for f in deploy_dir.rglob('*'):
        if f.is_file() and not any(x in f.parts for x in ['__pycache__', '.git']):
            target_files.append(f)

# 收集配置和文档
for pattern in ['manifest*.json', '*.sh', '*.md', '*.yml', '*.yaml']:
    for f in root.glob(pattern):
        if f.is_file():
            target_files.append(f)

# 去重并排序
seen = set()
unique_files = []
for f in target_files:
    if f not in seen:
        seen.add(f)
        unique_files.append(f)

with zipfile.ZipFile('m20-patrol-robot.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
    for f in sorted(unique_files):
        arcname = str(f.relative_to(root))
        zf.write(f, arcname)

sha = hashlib.sha256(open('m20-patrol-robot.zip', 'rb').read()).hexdigest()
size = os.path.getsize('m20-patrol-robot.zip')

print(f"✅ 部署包构建完成")
print(f"文件名: m20-patrol-robot.zip")
print(f"大小: {size:,} bytes ({size/1024:.1f} KB)")
print(f"SHA-256: {sha}")
print(f"文件数量: {len(unique_files)}")
