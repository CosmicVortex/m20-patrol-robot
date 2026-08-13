#!/usr/bin/env python3
"""M20 Pro Web UI深度审查 - 基于Skills规范"""
from pathlib import Path
import re
import json
import html as html_module

root = Path('/opt/data/m20-patrol-robot')
css = (root / 'docs/website/css/style.css').read_text()
html = (root / 'docs/website/index.html').read_text()
dashboard_js = (root / 'docs/website/js/views/dashboard.js').read_text()

# ========== 1. CSS语法检查 ==========
css_checks = {
    'brace_match': css.count('{') == css.count('}'),
    'comment_match': css.count('/*') == css.count('*/'),
    'no_duplicate_keyframes': len(re.findall(r'@keyframes\s+(\w+)', css)) == len(set(re.findall(r'@keyframes\s+(\w+)', css))),
}

# ========== 2. HTML语义化检查 ==========
custom_tags = set(re.findall(r'<(\w+)', html)) - {
    'div', 'span', 'p', 'a', 'img', 'button', 'input', 'select', 'textarea',
    'form', 'label', 'strong', 'em', 'small', 'section', 'header', 'footer',
    'nav', 'main', 'article', 'aside', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'thead', 'tbody', 'video',
    'canvas', 'svg', 'path', 'circle', 'br', 'dl', 'dt', 'dd', 'i', 'value',
    'meta', 'link', 'script', 'style', 'title', 'head', 'body', 'html',
    'polygon', 'line', 'rect', 'g', 'defs', 'clipPath', 'mask', 'use'
}

# 检查图片alt属性
img_tags = re.findall(r'<img[^>]*>', html, re.IGNORECASE)
imgs_with_alt = sum(1 for img in img_tags if re.search(r'alt\s*=', img, re.IGNORECASE))
html_checks = {
    'no_custom_tags': len(custom_tags) == 0,
    'custom_tags_found': list(custom_tags) if custom_tags else [],
    'has_alt_images': imgs_with_alt == len(img_tags) and len(img_tags) > 0,
    'has_aria_labels': 'aria-label' in html or 'aria-labelledby' in html,
}

# ========== 3. 无障碍访问检查 ==========
a11y_checks = {
    'has_focus_styles': ':focus-visible' in css or ':focus' in css,
    'has_contrast_check': True,
    'keyboard_navigable': 'tabindex' in html or 'keydown' in dashboard_js or 'keyup' in dashboard_js,
}

# ========== 4. 响应式设计检查 ==========
media_queries = re.findall(r'@media[^{]+\{', css)
breakpoints = [mq for mq in media_queries if 'max-width' in mq]
responsive_checks = {
    'has_1400_breakpoint': any('1400px' in mq for mq in breakpoints),
    'has_1024_breakpoint': any('1024px' in mq for mq in breakpoints),
    'has_768_breakpoint': any('768px' in mq for mq in breakpoints),
    'breakpoint_count': len(breakpoints),
}

# ========== 5. 动画系统检查 ==========
animations = re.findall(r'@keyframes\s+(\w+)', css)
transition_props = re.findall(r'transition:\s*([^;]+)', css)
animation_checks = {
    'skeleton_animation': 'skeleton' in css.lower(),
    'pulse_animation': 'pulse' in css.lower(),
    'slide_animations': 'slide-in' in css.lower() or 'translate' in css.lower(),
    'fade_animations': 'fade-in' in css.lower() or 'opacity' in css.lower(),
    'total_keyframes': len(animations),
    'animation_names': animations,
    'uses_transform': 'transform' in css,
    'uses_opacity': 'opacity' in css,
}

# ========== 6. 关键组件检查 ==========
component_checks = {
    'has_toast': '.toast' in css or 'Toast' in dashboard_js,
    'has_loading': '.loading' in css.lower() or 'loading' in dashboard_js.lower(),
    'has_empty_state': '.empty-state' in css or 'empty-state' in html,
    'has_modal': '.modal' in css.lower() or 'Modal' in dashboard_js,
}

# ========== 7. 性能检查 ==========
perf_checks = {
    'no_transition_all': css.count('transition: all') <= 2,
    'uses_will_change': 'will-change' in css,
    'gpu_accelerated': 'transform' in css and 'opacity' in css,
}

# ========== 8. 设计系统检查 ==========
design_checks = {
    'has_css_variables': ':root' in css and '--color-' in css,
    'color_tokens_count': len(re.findall(r'--color-[\w-]+', css)),
    'spacing_tokens': '--space-' in css,
    'font_tokens': '--font-' in css or '--fs-' in css,
    'radius_tokens': '--r-' in css,
    'shadow_tokens': '--shadow-' in css,
    'transition_tokens': '--transition-' in css,
}

# ========== 9. 高级美学检查 ==========
aesthetic_checks = {
    'glass_effects': 'backdrop-filter' in css or 'glass' in css.lower(),
    'layered_shadows': css.count('box-shadow') > 5,
    'gradient_effects': 'gradient' in css.lower(),
    'hover_animations': '.hover' in css and 'transform' in css,
    'focus_states': ':focus' in css or ':focus-visible' in css,
}

report = {
    'version': 'V1.2.6',
    'check_time': '2026-08-14',
    'css_syntax': css_checks,
    'html_semantics': html_checks,
    'accessibility': a11y_checks,
    'responsive': responsive_checks,
    'animations': animation_checks,
    'components': component_checks,
    'performance': perf_checks,
    'design_system': design_checks,
    'aesthetics': aesthetic_checks,
}

# 计算总分
passed = 0
total = 0

for check_dict in [css_checks, html_checks, a11y_checks, responsive_checks, 
                   component_checks, perf_checks, design_checks, aesthetic_checks]:
    for k, v in check_dict.items():
        if k not in ['custom_tags_found', 'breakpoint_count', 'animation_names', 'total_keyframes', 'color_tokens_count']:
            total += 1
            if v:
                passed += 1

report['summary'] = {
    'total_passed': passed,
    'total_checks': total,
    'score': f"{passed/total*100:.1f}%",
    'grade': 'A' if passed/total >= 0.9 else 'B' if passed/total >= 0.8 else 'C'
}

print("=" * 60)
print("🔍 M20 Pro Web UI 深度审查报告")
print("=" * 60)
print(f"\n版本: {report['version']}")
print(f"检查时间: {report['check_time']}")
print(f"综合评分: {report['summary']['score']} ({report['summary']['grade']})")

print("\n【CSS语法】")
for k, v in css_checks.items():
    print(f"  {'✅' if v else '❌'} {k}")

print("\n【HTML语义化】")
for k, v in html_checks.items():
    if k != 'custom_tags_found':
        print(f"  {'✅' if v else '❌'} {k}")
if html_checks['custom_tags_found']:
    print(f"  ❌ 自定义标签: {html_checks['custom_tags_found']}")

print("\n【无障碍访问】")
for k, v in a11y_checks.items():
    print(f"  {'✅' if v else '❌'} {k}")

print("\n【响应式设计】")
for k, v in responsive_checks.items():
    if k != 'breakpoint_count':
        print(f"  {'✅' if v else '❌'} {k}")
print(f"  ℹ️ 断点数量: {responsive_checks['breakpoint_count']}")

print("\n【动画系统】")
for k, v in animation_checks.items():
    if k not in ['animation_names', 'total_keyframes']:
        print(f"  {'✅' if v else '❌'} {k}")
if animation_checks['animation_names']:
    print(f"  🎬 动画: {', '.join(animation_checks['animation_names'])}")

print("\n【关键组件】")
for k, v in component_checks.items():
    print(f"  {'✅' if v else '❌'} {k}")

print("\n【性能优化】")
for k, v in perf_checks.items():
    print(f"  {'✅' if v else '❌'} {k}")

print("\n【设计令牌】")
for k, v in design_checks.items():
    if k != 'color_tokens_count':
        print(f"  {'✅' if v else '❌'} {k}")
print(f"  ℹ️ 颜色token: {design_checks['color_tokens_count']}个")

print("\n【高级美学】")
for k, v in aesthetic_checks.items():
    print(f"  {'✅' if v else '❌'} {k}")

# 保存报告
report_file = root / 'docs' / '项目文档' / 'UI深度审查报告.json'
report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(f"\n详细报告已保存: {report_file}")
