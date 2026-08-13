#!/usr/bin/env python3
"""CSS美学优化修复脚本 - 基于Skills规范"""
from pathlib import Path
import re

css_path = Path('/opt/data/m20-patrol-robot/docs/website/css/style.css')
css = css_path.read_text()

changes = []

# 1. 修复重复的@keyframes pulse
# 找到所有pulse动画定义
pulse_matches = list(re.finditer(r'@keyframes\s+pulse\b', css))
if len(pulse_matches) > 1:
    # 保留第一个，删除后面的
    for match in pulse_matches[1:]:
        # 找到对应的闭合括号
        end_pos = css.find('}', match.end())
        if end_pos != -1:
            # 检查是否还有其他关键帧在中间
            between = css[match.end():end_pos+1]
            if 'animation:' not in between or '@keyframes' in between:
                # 删除这个重复定义
                css = css[:match.start()] + css[end_pos+1:]
                changes.append(f"移除重复@keyframes pulse定义")

# 2. 修复transition: all - 替换为具体属性
# 对于按钮、卡片等交互元素，使用具体的transition属性
transition_replacements = [
    (r'transition:\s*all\s+var\(--transition-fast\)', 'transition-property: color, background-color, border-color, box-shadow; transition-duration: var(--transition-fast); transition-timing-function: ease;'),
    (r'transition:\s*all\s+var\(--transition-base\)', 'transition-property: color, background-color, border-color, box-shadow, transform; transition-duration: var(--transition-base); transition-timing-function: ease;'),
    (r'transition:\s*all\s+300ms\s+cubic-bezier\(0\.4,\s*0,\s*0\.2,\s*1\)', 'transition-property: transform, opacity; transition-duration: 300ms; transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);'),
    (r'transition:\s*all\s+0\.2s\s+ease', 'transition-property: color, background-color, border-color, box-shadow; transition-duration: 0.2s; transition-timing-function: ease;'),
]

for pattern, replacement in transition_replacements:
    count = len(re.findall(pattern, css))
    if count > 0:
        css = re.sub(pattern, replacement, css)
        changes.append(f"优化{count}处transition: all → 具体属性")

# 3. 添加will-change用于动画元素
# 在animation定义后添加will-change
animation_blocks = re.findall(r'\.(\w+)\s*\{[^}]*animation:', css)
for block in animation_blocks:
    # 检查是否已有will-change
    if f'.{block}' not in css or 'will-change' not in css:
        # 在类定义中添加will-change
        class_pattern = rf'(\.{block}\s*\{{[^}}]*animation:[^}}]*\}})'
        if re.search(class_pattern, css, re.DOTALL):
            css = re.sub(class_pattern, rf'\1\n  will-change: transform, opacity;', css, flags=re.DOTALL)
            changes.append(f"为.{block}添加will-change")

# 4. 添加hover transform过渡优化
# 确保所有使用transform的hover都有正确的过渡
hover_transform_fixes = [
    (r'(\.btn:hover[^{]*)\{([^}]*?)transform:\s*scale\(([^)]+)\)', r'\1 {\2transition: transform 200ms ease;\3'),
    (r'(\.card:hover[^{]*)\{([^}]*?)transform:\s*translateY\(([^)]+)\)', r'\1 {\2transition: transform 300ms ease;\3'),
]

for pattern, replacement in hover_transform_fixes:
    count = len(re.findall(pattern, css, re.DOTALL))
    if count > 0:
        css = re.sub(pattern, replacement, css, flags=re.DOTALL)
        changes.append(f"优化{count}处hover transform过渡")

# 保存修改
css_path.write_text(css)

print("=" * 60)
print("✅ CSS美学优化修复完成")
print("=" * 60)
print(f"\n共应用 {len(changes)} 项修复:")
for i, change in enumerate(changes, 1):
    print(f"  {i}. {change}")
print(f"\n文件已更新: {css_path}")
