#!/usr/bin/env python3
"""M20 Pro UI/UX视觉评分系统"""
from pathlib import Path
import re
import json

# 读取关键文件
css = Path("docs/website/css/style.css").read_text()
html = Path("docs/website/index.html").read_text()
dashboard_js = Path("docs/website/js/views/dashboard.js").read_text()
app_js = Path("docs/website/js/app.js").read_text()

# 评分维度
scores = {
    "配色体系": {"score": 0, "max": 20, "issues": []},
    "布局比例": {"score": 0, "max": 20, "issues": []},
    "字体排版": {"score": 0, "max": 15, "issues": []},
    "交互体验": {"score": 0, "max": 20, "issues": []},
    "数据展示": {"score": 0, "max": 15, "issues": []},
    "无障碍访问": {"score": 0, "max": 10, "issues": []},
}

# ========== 1. 配色体系评分 ==========
print("=" * 60)
print("【配色体系】(20分)")
print("=" * 60)

brand_colors = re.findall(r'--color-brand-[\w-]+:\s*#[0-9a-fA-F]{6}', css)
print(f"品牌色定义: {len(brand_colors)} 个")
if len(brand_colors) >= 3:
    scores["配色体系"]["score"] += 5

bg_colors = re.findall(r'--color-bg-[\w-]+:\s*#[0-9a-fA-F]{6}', css)
print(f"背景色定义: {len(bg_colors)} 个")
if len(bg_colors) >= 5:
    scores["配色体系"]["score"] += 4

status_colors = ["--color-success", "--color-warning", "--color-error", "--color-info"]
for color in status_colors:
    if color in css:
        scores["配色体系"]["score"] += 1.5

disabled_color = re.search(r'--color-text-disabled:\s*#([0-9a-fA-F]{6})', css)
if disabled_color:
    hex_color = disabled_color.group(1)
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    contrast = (1.05 - 0.05) / (luminance * 0.05 + (1 - luminance))
    if contrast >= 3:
        scores["配色体系"]["score"] += 3
        print(f"✅ 禁用文字对比度: {contrast:.1f}:1")

print(f"当前得分: {scores['配色体系']['score']}/20\n")

# ========== 2. 布局比例评分 ==========
print("=" * 60)
print("【布局比例】(20分)")
print("=" * 60)

sidebar_width = re.search(r'\.sidebar\s*\{[^}]*width:\s*(\d+)px', css)
if sidebar_width:
    width = int(sidebar_width.group(1))
    if width >= 260:
        scores["布局比例"]["score"] += 5
        print(f"✅ 侧边栏宽度: {width}px")

grid_patterns = re.findall(r'grid-template-columns:', css)
print(f"网格布局定义: {len(grid_patterns)} 处")
if len(grid_patterns) >= 2:
    scores["布局比例"]["score"] += 4

breakpoints = re.findall(r'@media\s*\([^)]*max-width:\s*(\d+)px\)', css)
print(f"响应式断点: {breakpoints}")
if len(breakpoints) >= 2:
    scores["布局比例"]["score"] += 4

print(f"当前得分: {scores['布局比例']['score']}/20\n")

# ========== 3. 字体排版评分 ==========
print("=" * 60)
print("【字体排版】(15分)")
print("=" * 60)

font_families = re.findall(r'--font-[\w-]+:', css)
if len(font_families) >= 3:
    scores["字体排版"]["score"] += 4

font_sizes = re.findall(r'--fs-[\w-]+:\s*[\d.]+rem', css)
if len(font_sizes) >= 6:
    scores["字体排版"]["score"] += 4

line_heights = re.findall(r'--lh-[\w-]+:', css)
if len(line_heights) >= 2:
    scores["字体排版"]["score"] += 3

tabular_nums = css.count('tabular-nums')
if tabular_nums > 0:
    scores["字体排版"]["score"] += 2

print(f"当前得分: {scores['字体排版']['score']}/15\n")

# ========== 4. 交互体验评分 ==========
print("=" * 60)
print("【交互体验】(20分)")
print("=" * 60)

alert_uses = dashboard_js.count('alert(') + app_js.count('alert(')
confirm_uses = dashboard_js.count('confirm(') + app_js.count('confirm(')
print(f"alert() 使用: {alert_uses} 次")
print(f"confirm() 使用: {confirm_uses} 次")

if alert_uses == 0 and confirm_uses == 0:
    scores["交互体验"]["score"] += 8
    print("✅ 无原生alert/confirm，使用Toast")
else:
    scores["交互体验"]["issues"].append(f"残留 {alert_uses + confirm_uses} 处原生对话框")

button_states = ['hover', 'focus', 'active', 'disabled']
button_styles = sum(1 for state in button_states if f':{state}' in css)
if button_styles >= 3:
    scores["交互体验"]["score"] += 5

click_targets = css.count('min-height: 44px') + css.count('min-width: 44px')
if click_targets > 0:
    scores["交互体验"]["score"] += 4

loading_states = css.count('.spinner') + css.count('loading')
if loading_states > 0:
    scores["交互体验"]["score"] += 3

print(f"当前得分: {scores['交互体验']['score']}/20\n")

# ========== 5. 数据展示评分 ==========
print("=" * 60)
print("【数据展示】(15分)")
print("=" * 60)

empty_states_check = '暂无数据' in html or '未连接' in html
if empty_states_check:
    scores["数据展示"]["score"] += 4
    print("✅ 空状态使用语义化文本")

big_numbers = css.count('.big-number') + css.count('font-size: var(--fs-2xl)')
if big_numbers > 0:
    scores["数据展示"]["score"] += 3

refresh_interval = re.search(r'setInterval.*?(\d+)\s*\*', dashboard_js)
if refresh_interval:
    interval = int(refresh_interval.group(1))
    if interval <= 5000:
        scores["数据展示"]["score"] += 3
        print(f"✅ 刷新频率: {interval}ms")

print(f"当前得分: {scores['数据展示']['score']}/15\n")

# ========== 6. 无障碍访问评分 ==========
print("=" * 60)
print("【无障碍访问】(10分)")
print("=" * 60)

aria_labels = html.count('aria-label') + html.count('aria-current')
print(f"ARIA标签: {aria_labels} 处")
if aria_labels >= 3:
    scores["无障碍访问"]["score"] += 4

semantic_tags = ['<header', '<main', '<aside', '<nav', '<footer']
semantic_count = sum(1 for tag in semantic_tags if tag in html)
print(f"语义化标签: {semantic_count} 个")
if semantic_count >= 4:
    scores["无障碍访问"]["score"] += 3

keyboard_nav = css.count(':focus')
print(f"键盘焦点样式: {keyboard_nav} 处")
if keyboard_nav > 0:
    scores["无障碍访问"]["score"] += 3

print(f"当前得分: {scores['无障碍访问']['score']}/10\n")

# ========== 总分计算 ==========
print("=" * 60)
print("【评分汇总】")
print("=" * 60)

total_score = sum(s["score"] for s in scores.values())
total_max = sum(s["max"] for s in scores.values())
percentage = (total_score / total_max) * 100

print(f"\n{'维度':<12} {'得分':>8} {'满分':>6} {'占比':>8}")
print("-" * 40)
for name, data in scores.items():
    pct = (data["score"] / data["max"]) * 100
    print(f"{name:<12} {data['score']:>7.1f} {data['max']:>5} {pct:>7.1f}%")

print("-" * 40)
print(f"{'总计':<12} {total_score:>7.1f} {total_max:>5} {percentage:>7.1f}%")

print("\n" + "=" * 60)
print("【总体评价】")
print("=" * 60)

if percentage >= 85:
    grade = "A - 优秀"
    comment = "UI/UX设计达到工业级标准，品牌视觉统一，交互体验流畅"
elif percentage >= 70:
    grade = "B - 良好"
    comment = "整体设计良好，有部分细节需要优化"
elif percentage >= 60:
    grade = "C - 及格"
    comment = "基本可用，但存在明显的体验问题"
else:
    grade = "D - 需改进"
    comment = "存在严重的设计缺陷，需要全面重构"

print(f"\n评分等级: {grade} ({percentage:.1f}%)")
print(f"评价说明: {comment}\n")

if scores["交互体验"]["issues"]:
    print("⚠️  关键问题:")
    for issue in scores["交互体验"]["issues"]:
        print(f"  • {issue}")

result = {
    "total_score": total_score,
    "total_max": total_max,
    "percentage": round(percentage, 1),
    "grade": grade,
    "dimensions": {name: {"score": data["score"], "max": data["max"], "issues": data["issues"]} 
                  for name, data in scores.items()}
}

with open("docs/项目文档/UI视觉评分报告.json", "w") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n✅ 评分结果已保存")
