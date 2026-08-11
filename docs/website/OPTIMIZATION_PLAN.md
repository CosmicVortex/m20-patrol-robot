# M20 Pro 巡检仪表盘 UI 优化执行方案

## 优化目标
在保持现有页面布局结构不变的前提下，全面优化视觉表现和交互体验。

## 执行清单

### 1. 视觉设计优化
- [x] 引入 Phosphor Icons（专业图标库）
- [x] 优化配色方案（更深邃的蓝黑背景、更好的对比度）
- [x] 引入 Inter + JetBrains Mono 字体组合
- [x] 改进卡片阴影和边框发光效果
- [x] 优化按钮和交互元素视觉层次

### 2. 交互体验优化
- [x] 添加页面加载骨架屏动画
- [x] 数据卡片悬停效果（轻微上浮 + 边框发光）
- [x] 状态徽章过渡动画
- [x] 电池电量可视化进度条
- [x] 连接状态实时显示延迟

### 3. 功能增强
- [x] 登录界面优化（更好的视觉反馈）
- [x] 机器人状态面板改进
- [x] 时间线状态指示优化
- [x] 相机状态可视化改进
- [x] 告警计数动画效果

### 4. 约束检查
- [x] 保持所有现有 DOM 结构和 id 不变
- [x] 保持所有 JavaScript 逻辑不变
- [x] 响应式断点保持不变
- [x] 不引入外部 JS 库

## 设计读取
"Reading this as: industrial monitoring dashboard for automotive service center, with a professional dark-tech aesthetic, leaning toward Carbon Design System principles + restrained motion."

## 配色方案（优化后）
- 主背景: `#060c18` (更深邃的午夜蓝)
- 面板背景: `#0b1525` → `#101d35` (分层深度)
- 边框: `rgba(74,168,210,0.18)` → `rgba(74,168,210,0.28)` (柔和发光)
- 强调色: `#4aa8d2` (专业青蓝)
- 成功色: `#5bc87a` (清新绿)
- 警告色: `#e8a84b` (琥珀色)
- 危险色: `#e8646c` (柔和红)
- 文字主色: `#e8edf5` (冷白)
- 文字次色: `#8a9bbf` (灰蓝)

## 字体方案
- 正文: `"Inter", "PingFang SC", "Microsoft YaHei", sans-serif`
- 数字: `"JetBrains Mono", "Roboto Mono", monospace`
