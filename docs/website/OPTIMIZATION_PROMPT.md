# M20 Pro 巡检仪表盘 UI 优化提示词

## 设计目标
保持现有页面布局结构不变，仅优化视觉表现和交互体验。

## 设计读取
"Reading this as: industrial monitoring dashboard for automotive service center, with a professional dark-tech aesthetic, leaning toward Carbon Design System + restrained motion."

## 配色方案
- 主背景: `#080f1e` (更深邃的午夜蓝)
- 面板背景: `#0d1a2d` → `#111d32` (分层深度)
- 边框: `rgba(91,200,237,0.2)` → `rgba(91,200,237,0.25)` (柔和发光)
- 强调色: `#4db8e8` (青蓝，降低饱和度)
- 成功色: `#5bc87a` (清新绿)
- 警告色: `#e8a84b` (琥珀色)
- 危险色: `#e8646c` (柔和红)
- 文字主色: `#e8edf5` (冷白)
- 文字次色: `#8a9bbf` (灰蓝)

## 图标方案
使用 Phosphor Icons CDN (lightweight, professional):
```html
<link rel="stylesheet" href="https://unpkg.com/@phosphor-icons/web@2.0.3/src/bold/style.css">
```
替换所有 Unicode 符号为 `<i class="ph ph-icon-name"></i>` 格式。

## 字体优化
- 系统字体栈: `"Inter", "PingFang SC", "Microsoft YaHei", sans-serif`
- 数字: `"JetBrains Mono", "Roboto Mono", monospace` (等宽数字，便于对齐)
- 标题: 18px → 20px, 加粗 600
- 正文: 13px → 14px, 行高 1.5
- 标注: 11px → 12px

## 交互优化
1. **加载骨架屏**: 数据加载时显示 shimmer 动画占位
2. **状态过渡**: badge 颜色变化添加 transition
3. **悬停反馈**: 卡片 hover 时轻微上浮 + 边框发光
4. **数字动画**: 数值变化时使用滚动动画
5. **连接状态**: 实时显示 ping 延迟

## 功能增强
1. **电池可视化**: 用进度条替代纯数字，带颜色阈值
2. **运动状态指示器**: 用动态图标 + 文字组合
3. **告警时间线**: 错误列表显示在最近异常时间
4. **快捷操作栏**: 顶部工具栏添加常用操作按钮
5. **主题切换**: 支持明/暗主题切换

## 约束
- 不改变现有 DOM 结构层级
- 保持所有 id 和 class 命名兼容现有 JS
- 响应式断点保持不变
- 不引入外部 JS 库（仅 CSS + 原生 JS）
- 保持所有功能逻辑不变
