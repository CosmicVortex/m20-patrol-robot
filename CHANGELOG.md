# 版本历史

## V1.1.4 (2026-08-15)

### 改进
- 文档规范化整理：删除过程性文档，优化目录结构
- API文档完善：补充work-orders/update接口，修正演示示例
- manifest字段对齐：runtime_mode统一为realtime_readonly

### 修复
- 云台方法名修正：move_gimbal→set_angle，zoom_gimbal→zoom_to

---

## V1.1.3 (2026-08-13)

### 修复
- 替换非标准`<value>`标签为`<span class="gimbal-val">`（4处云台参数显示）
- 移除重复的@keyframes定义（spin/fadeIn）
- 添加.gimbal-val样式类
- 修复CSS括号匹配问题（306对括号）

### 改进
- Web UI现代化：添加动画效果（shimmer/pulse/slide-in/fade-in）
- 响应式设计完善：1400px/1024px/768px断点
- 空状态提示优化："暂无数据"/"未连接"

---

## V1.1.2 (2026-08-13)

### 新功能
- 双电池支持：前后电池独立显示（前电池92% + 后电池88%）
- 权限完全开放：auth_enabled=false, allow_anonymous=true
- 自动登录：无需认证即可访问

### 改进
- 连接失败时生成fallback数据
- 模拟器模式返回完整mock数据
- 2秒轮询机制优化

---
