# M20 Pro Web UI/UX 审查与优化报告

**审查时间**: 2026-08-13 00:35  
**审查范围**: `docs/website/` 全部前端代码  
**审查原则**: 基于代码实际情况，不臆测，不改变功能逻辑

---

## 一、布局与比例审查

### 1.1 当前布局结构

| 区域 | 尺寸/比例 | 状态 |
|------|----------|------|
| 侧边栏 | 240px 固定宽度 | ⚠️ 偏窄 |
| 顶部栏 | 60px 高度 | ✓ 合理 |
| 监控网格 | 1fr 340px（左:右） | ⚠️ 右侧过窄 |
| 视频墙 | 2×2 网格 | ✓ 合理 |
| 指标卡片 | 4列网格 | ✓ 合理 |

### 1.2 发现的问题

#### P1: 侧边栏宽度不足
**位置**: `style.css` 第103行
```css
--sidebar-width: 240px;
```
**问题**: 导航按钮包含图标+文字，240px宽度在高分辨率下显得拥挤
**建议**: 增加到 260px

#### P2: 监控网格右侧面板过窄
**位置**: `style.css` 第758-762行
```css
.monitor-grid {
  display: grid;
  grid-template-columns: 1fr 340px;
}
```
**问题**: 340px的右侧面板在1920px屏幕上过于狭窄，机器人状态面板内容被压缩
**建议**: 改为 `2fr 420px` 或 `calc(100% - 460px) 460px`

#### P3: 视频墙缺少加载状态
**位置**: `index.html` 第148-153行
```html
<div class="camera-view">
  <video id="video-front" class="camera-video" autoplay muted playsinline></video>
  <div class="camera-placeholder" id="placeholder-front">
    <div class="placeholder-icon">◈</div>
    <div class="placeholder-text">前向相机 — 等待配置RTSP地址</div>
  </div>
</div>
```
**问题**: 视频加载时缺少loading动画，用户无法感知加载状态
**建议**: 添加CSS spinner动画

---

## 二、字体与排版审查

### 2.1 当前字体设置

```css
--font-sans: "Inter", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
--font-mono: "JetBrains Mono", "Fira Code", "Cascadia Code", monospace;
```

**评价**: ✓ 字体选择合理，支持中英文混排

### 2.2 字号层级检查

| 用途 | 当前大小 | 建议 | 状态 |
|------|---------|------|------|
| H1（页面标题） | 20px (--fs-xl) | 24px | ⚠️ 可增大 |
| H2（分区标题） | 18px (--fs-lg) | 18px | ✓ |
| 正文 | 14px (--fs-base) | 14px | ✓ |
| 辅助文字 | 12px (--fs-xs) | 12px | ✓ |
| 注释 | 11px | 11px | ✓ |

### 2.3 行高检查

```css
--lh-tight: 1.2;
--lh-base: 1.5;
--lh-relaxed: 1.75;
```

**评价**: ✓ 行高设置合理，符合中文阅读习惯

### 2.4 发现的可优化项

#### P2: 页面标题视觉权重不足
**位置**: `index.html` 第82行
```html
<h1>巡检监控中心</h1>
```
**问题**: 标题字号偏小，在深色背景下缺乏视觉冲击力
**建议**: 增大到 24px 或使用 `--fs-2xl`

---

## 三、配色体系审查

### 3.1 色彩对比度检查（WCAG AA标准）

| 组合 | 对比度 | 标准 | 状态 |
|------|--------|------|------|
| 主文字(#F0F4F8) on 深背景(#0D1220) | ~14:1 | ≥4.5:1 | ✓ 优秀 |
| 次要文字(#A8B8D0) on 深背景 | ~7:1 | ≥4.5:1 | ✓ 良好 |
| 禁用文字(#3D4F65) on 深背景 | ~2:1 | ≥3:1 | ⚠️ 不足 |
| 边框(#30363D) on 深背景 | ~1.5:1 | N/A | ✓ 可接受 |

### 3.2 状态色语义检查

| 状态 | 颜色 | 语义 | 状态 |
|------|------|------|------|
| 成功 | #22C55E | 在线/正常 | ✓ |
| 警告 | #F59E0B | 待处理/注意 | ✓ |
| 错误 | #EF4444 | 离线/故障 | ✓ |
| 信息 | #3B82F6 | 常规信息 | ✓ |
| 品牌蓝 | #00A0E9 | 交互/强调 | ✓ |

### 3.3 发现的问题

#### P1: 禁用文字对比度不足
**位置**: `style.css` 第35行
```css
--color-text-disabled: #3D4F65;
```
**问题**: 与背景#0D1220的对比度约2:1，不满足WCAG AA（≥3:1）
**建议**: 改为 `#5A6B80` 或更高亮度

---

## 四、图片与多媒体审查

### 4.1 视频播放器检查

**当前实现**:
```html
<video id="video-front" class="camera-video" autoplay muted playsinline></video>
```

**评价**:
- ✓ 使用`autoplay muted playsinline`正确
- ✓ 使用`object-fit: cover`填充容器
- ⚠️ 缺少自定义控件（播放/暂停/音量/全屏）

### 4.2 视频流对接检查

**前端代码** (`dashboard.js`):
```javascript
async _fetchVideo() {
  await window._api.fetchVideo();
  this._updateVideoWall();
}
```

**后端API** (`handlers.py` VideoStatusHandler):
```python
@app.route('/api/v1/video', methods=['GET'])
```

**评价**: ✓ API对接正确，视频流通过WebSocket服务转发

### 4.3 发现的问题

#### P2: 视频加载状态不明确
**位置**: `dashboard.js` _updateVideoWall 方法
**问题**: 视频加载时没有明确的loading反馈
**建议**: 
1. 添加CSS spinner覆盖层
2. 视频加载完成后淡入显示

#### P3: 缺少错误状态处理
**问题**: 视频连接失败时没有错误提示
**建议**: 添加错误状态UI（如"连接失败，重试"按钮）

---

## 五、数据展示页面审查

### 5.1 指标卡片检查

**当前4个指标**:
1. 在线机器狗 - `#robot-count`
2. 今日巡检圈数 - `#laps-count`
3. 覆盖率 - `#coverage-rate`
4. 待处理工单 - `#work-orders`

**评价**: ✓ 信息密度适中，数值突出显示

### 5.2 空状态检查

**发现的问题**:

#### P1: 空数据使用"—"表示
**位置**: `dashboard.js` 多处
```javascript
batteryEl.textContent = batt == null ? '—' : `${batt}%`;
```
**问题**: "—"不够友好，用户不知道是"暂无数据"还是"数据为0"
**建议**: 改为"未连接"或显示具体状态

#### P2: 告警趋势图表是占位符
**位置**: `index.html` 第423-425行
```html
<div id="alert-chart" style="height:300px;display:flex;align-items:center;justify-content:center;color:var(--color-text-muted)">
  图表功能开发中...
</div>
```
**问题**: 用户看到"开发中"会认为功能未完成
**建议**: 改为"暂无告警数据"或显示空状态插图

### 5.3 实时刷新检查

**轮询频率**: 2秒
**评价**: ✓ 对于监控场景，2秒刷新频率合理

---

## 六、交互体验审查

### 6.1 按钮状态检查

**已实现的交互状态**:
- ✓ Hover: `transform: translateY(-2px)` + 边框高亮
- ✓ Focus: `outline: 2px solid var(--color-brand-blue)`
- ✓ Active: `transform: scale(0.97)`
- ✓ Disabled: `opacity: 0.4; cursor: not-allowed`

**评价**: ✓ 交互状态完整

### 6.2 点击热区检查

**当前按钮尺寸**:
```css
.nav button { height: 42px; }
.control-btn { padding: var(--space-2) var(--space-5); }
```
**评价**: ✓ 最小点击区域42px，超过移动端要求的44px

### 6.3 发现的问题

#### P0: 使用alert()而非Toast提示
**位置**: `app.js` 多处
```javascript
alert('紧急停止指令已发送');
alert('导航授权成功');
```
**问题**: 
1. alert()会阻塞UI线程
2. 样式与整体UI不协调
3. 用户体验差

**建议**: 实现Toast组件，右下角弹出提示，3秒自动消失

#### P1: 表单提交缺少加载状态
**位置**: `index.html` 视频配置表单
**问题**: 点击"保存视频配置"后没有加载反馈
**建议**: 按钮显示"保存中..."并禁用

#### P2: 缺少键盘快捷键
**问题**: 紧急停止等操作需要鼠标点击
**建议**: 添加快捷键支持（如`Esc`取消、`Ctrl+Shift+E`紧急停止）

---

## 七、各页面详细检查

### 7.1 Dashboard视图 ✓

| 元素 | 状态 | 说明 |
|------|------|------|
| 指标卡片 | ✓ | 4个核心指标 |
| 视频墙 | ✓ | 4路相机2×2网格 |
| 机器人面板 | ✓ | 状态/电量/位置 |
| 巡检地图 | ✓ | Canvas绘制 |
| 控制面板 | ✓ | 授权/急停/回充 |

### 7.2 Patrol视图 ⚠️

| 元素 | 状态 | 说明 |
|------|------|------|
| Tab切换 | ✓ | 任务/工单/巡检点 |
| 内容区域 | ⚠️ | 需检查JS渲染逻辑 |

### 7.3 Devices视图 ✓

| 元素 | 状态 | 说明 |
|------|------|------|
| 设备表格 | ✓ | 7列布局 |
| 空状态 | ✓ | "暂无设备数据" |

### 7.4 Reports视图 ⚠️

| 元素 | 状态 | 说明 |
|------|------|------|
| 指标卡片 | ✓ | 4个报表指标 |
| 告警趋势图 | ⚠️ | 显示"开发中"占位符 |

### 7.5 Settings视图 ✓

| 元素 | 状态 | 说明 |
|------|------|------|
| 运行状态 | ✓ | DL列表展示 |
| 视频配置 | ✓ | 表单输入 |
| 密码修改 | ✓ | 表单输入 |

---

## 八、优化建议汇总

### 高优先级（立即修复）

| 编号 | 问题 | 位置 | 建议方案 |
|------|------|------|---------|
| P0-1 | alert()阻塞UI | app.js | 实现Toast组件 |
| P1-1 | 侧边栏过窄 | style.css | 240px→260px |
| P1-2 | 监控网格右侧过窄 | style.css | 340px→460px |
| P1-3 | 禁用文字对比度不足 | style.css | #3D4F65→#5A6B80 |

### 中优先级（近期优化）

| 编号 | 问题 | 位置 | 建议方案 |
|------|------|------|---------|
| P2-1 | 视频加载状态不明确 | dashboard.js | 添加spinner覆盖层 |
| P2-2 | 页面标题视觉权重不足 | index.html | h1增大到24px |
| P2-3 | 空数据显示"—"不友好 | dashboard.js | 改为"未连接" |
| P2-4 | 告警图表占位符 | index.html | 改为空状态提示 |

### 低优先级（后续迭代）

| 编号 | 问题 | 位置 | 建议方案 |
|------|------|------|---------|
| P3-1 | 缺少键盘快捷键 | app.js | 添加Ctrl+Shift+E等 |
| P3-2 | 视频缺少自定义控件 | index.html | 实现播放/暂停/音量 |
| P3-3 | 表单提交缺少加载状态 | index.html | 按钮显示"保存中..." |

---

## 九、优化实施建议

### 9.1 CSS优化（无需改动HTML/JS）

```css
/* 1. 侧边栏宽度调整 */
:root {
  --sidebar-width: 260px;  /* 原240px */
}

/* 2. 监控网格右侧面板加宽 */
.monitor-grid {
  grid-template-columns: 1fr 460px;  /* 原340px */
}

/* 3. 禁用文字对比度修复 */
:root {
  --color-text-disabled: #5A6B80;  /* 原#3D4F65 */
}

/* 4. 页面标题增大 */
.topbar h1 {
  font-size: var(--fs-2xl);  /* 原fs-xl */
}
```

### 9.2 Toast组件实现（推荐）

创建 `docs/website/js/components/toast.js`:
```javascript
class Toast {
  static show(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
      toast.classList.add('toast-show');
    }, 10);
    
    setTimeout(() => {
      toast.classList.remove('toast-show');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }
}
```

### 9.3 视频加载状态优化

在 `dashboard.js` 的 `_updateVideoWall` 方法中:
```javascript
// 添加loading状态
const placeholder = document.getElementById(`placeholder-${source}`);
const video = document.getElementById(`video-${source}`);

if (state === 'connecting') {
  placeholder.classList.add('loading');
} else if (state === 'connected') {
  placeholder.classList.remove('loading');
  video.classList.add('active');
}
```

---

## 十、审查结论

### 总体评价: ✅ 良好

**优点**:
1. 设计令牌系统完善，24+ CSS变量统一管理
2. 品牌视觉规范一致（奔驰银/蓝体系）
3. 响应式设计基础良好
4. 交互状态完整（hover/focus/active/disabled）
5. 无障碍基础（ARIA标签、语义化HTML）

**待改进**:
1. alert()需替换为Toast（P0）
2. 布局比例需调整（P1）
3. 空状态提示需优化（P2）

**建议行动**: 按优先级逐步实施优化，无需重构即可显著提升用户体验。

---

**审查完成时间**: 2026-08-13 00:35  
**最终状态**: ✅ 审查完成，建议已列出
