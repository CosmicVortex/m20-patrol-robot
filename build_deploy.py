#!/usr/bin/env python3
"""构建完整部署包 - 包含Web UI和后端代码"""
import zipfile, hashlib, os
from pathlib import Path

root = Path('.')

# 收集所有需要打包的文件
target_files = []

# 1. 后端Python代码（排除测试和缓存）
backend_dir = root / 'backend'
if backend_dir.exists():
    for f in backend_dir.rglob('*.py'):
        # 排除测试文件和缓存
        if 'test' not in str(f).lower() and '__pycache__' not in str(f):
            target_files.append(f)

# 2. Web UI文件
web_dir = root / 'docs' / 'website'
if web_dir.exists():
    for f in web_dir.rglob('*'):
        if f.is_file() and '__pycache__' not in str(f):
            target_files.append(f)

# 3. 部署脚本
deploy_dir = root / 'deploy'
if deploy_dir.exists():
    for f in deploy_dir.rglob('*'):
        if f.is_file() and not any(x in str(f) for x in ['.git', '.venv']):
            target_files.append(f)

# 4. 初始化脚本
for f in root.glob('init_*.py'):
    target_files.append(f)

# 过滤和打包
allowed_extensions = {'.py', '.html', '.css', '.js', '.json', '.png', '.jpg', '.svg', '.md', '.txt', '.sh'}
files = []
for f in target_files:
    if f.suffix.lower() in allowed_extensions:
        arcname = str(f.relative_to(root))
        # 跳过大的压缩文件
        if not arcname.endswith('.zip') and not arcname.endswith('.tar.gz'):
            files.append((f, arcname))

# 去重
seen = set()
unique_files = []
for fpath, arcname in files:
    if arcname not in seen:
        seen.add(arcname)
        unique_files.append((fpath, arcname))
files = unique_files

# 创建zip
zip_path = root / 'm20-patrol-robot.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for fpath, arcname in files:
        zf.write(fpath, arcname)

sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
size_kb = zip_path.stat().st_size / 1024

print(f"✅ 部署包构建完成")
print(f"文件名: m20-patrol-robot.zip")
print(f"大小: {zip_path.stat().st_size:,} bytes ({size_kb:.1f} KB)")
print(f"SHA-256: {sha[:16]}")
print(f"文件数量: {len(files)}")
print(f"\n包含内容:")
py_count = len([f for f in files if f[0].suffix == '.py'])
web_count = len([f for f in files if f[0].suffix in ['.html', '.css', '.js']])
deploy_count = len([f for f in files if 'deploy' in str(f[0]).lower()])
print(f"  - 后端Python代码: {py_count} 个文件")
print(f"  - Web UI文件: {web_count} 个文件")
print(f"  - 部署脚本: {deploy_count} 个文件")
