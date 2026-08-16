# 版本历史

## V1.1.6 (2026-08-16)

### 新功能
- **直接控制模式**：默认启用控制权限，无需额外授权操作
- **认证机制**：启用用户认证，默认密码123456
- **配置优化**：runtime_mode切换为realtime，read_only_mode=false

### 配置变更
| 配置项 | 旧值 | 新值 | 说明 |
|--------|------|------|------|
| runtime_mode | realtime_readonly | realtime | 完整控制模式 |
| read_only_mode | true | false | 允许写操作 |
| control_enabled | false | true | 启用控制功能 |
| auth_enabled | false | true | 启用认证 |
| allow_anonymous | true | false | 禁止匿名访问 |

### 代码变更
- 运动控制服务默认授权（开发测试模式）
- 清理注释掉的权限检查代码
- 更新测试用例以适配新的默认行为

### 门禁验证
- pytest: **232 passed** ✓
- JS语法: **全部通过** ✓

---

## V1.1.5 (2026-08-16)

### 改进
- Web UI深度优化：CSS增至59KB，新增GPU加速动画8处
- 设计令牌系统完善：--duration/--color-brand变体
- 无障碍支持增强：aria-live、role属性、.sr-only类
- 响应式断点扩展：新增480px移动端断点
- 提取50+内联样式为CSS类，零静态内联样式残留
- 门禁验证：232测试通过，CSS braces平衡
- 文档规范化：7份项目文档按内容重新命名，新增API参考与贡献指南

### 修复
- 补充--color-brand-dim/glow变体
- 合并重复的.input:focus定义
- 补全.modal-backdrop等缺失样式

---

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
