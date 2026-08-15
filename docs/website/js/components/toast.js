/**
 * Toast - 非阻塞式消息提示组件
 * 
 * 替换原 alert()/confirm() 调用，提供更友好的用户体验
 */
class Toast {
  static instances = new Map();
  
  /**
   * 显示成功提示
   */
  static success(message) {
    return this.show(message, 'success');
  }
  
  /**
   * 显示错误提示
   */
  static error(message) {
    return this.show(message, 'error');
  }
  
  /**
   * 显示警告提示
   */
  static warning(message) {
    return this.show(message, 'warning');
  }
  
  /**
   * 显示信息提示
   */
  static info(message) {
    return this.show(message, 'info');
  }
  
  /**
   * 显示通用提示
   */
  static show(message, type = 'info', duration = 3000) {
    // 生成唯一ID
    const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    // 创建Toast元素
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.id = id;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');
    
    // 图标
    const icons = {
      success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>',
      error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
      warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
      info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
    };
    
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || icons.info}</span>
      <span class="toast-message">${this.escapeHtml(message)}</span>
      <button class="toast-close" aria-label="关闭">×</button>
    `;
    
    // 关闭按钮
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => this.dismiss(id));
    
    // 添加到容器
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    container.appendChild(toast);
    
    // 触发动画
    requestAnimationFrame(() => {
      toast.classList.add('toast-show');
    });
    
    // 存储实例
    this.instances.set(id, { toast, timer: null });
    
    // 自动消失
    if (duration > 0) {
      const timer = setTimeout(() => this.dismiss(id), duration);
      this.instances.get(id).timer = timer;
    }
    
    return id;
  }
  
  /**
   * 移除Toast
   */
  static dismiss(id) {
    const instance = this.instances.get(id);
    if (!instance) return;
    
    const { toast, timer } = instance;
    
    if (timer) clearTimeout(timer);
    
    toast.classList.remove('toast-show');
    toast.classList.add('toast-hide');
    
    setTimeout(() => {
      toast.remove();
      this.instances.delete(id);
    }, 300);
  }
  
  /**
   * 确认对话框（替换 confirm()）
   */
  static async confirm(message, title = '确认操作') {
    return new Promise((resolve) => {
      const dialog = document.createElement('div');
      dialog.className = 'toast-confirm';
      dialog.innerHTML = `
        <div class="toast-confirm-overlay"></div>
        <div class="toast-confirm-box">
          <h3>${this.escapeHtml(title)}</h3>
          <p>${this.escapeHtml(message)}</p>
          <div class="toast-confirm-actions">
            <button class="btn btn-secondary" data-action="cancel">取消</button>
            <button class="btn btn-danger" data-action="confirm">确认</button>
          </div>
        </div>
      `;
      
      document.body.appendChild(dialog);
      
      const overlay = dialog.querySelector('.toast-confirm-overlay');
      const cancelBtn = dialog.querySelector('[data-action="cancel"]');
      const confirmBtn = dialog.querySelector('[data-action="confirm"]');
      
      const cleanup = () => {
        dialog.classList.add('toast-confirm-hide');
        setTimeout(() => dialog.remove(), 300);
      };
      
      const handleResult = (result) => {
        cleanup();
        resolve(result);
      };
      
      overlay.addEventListener('click', () => handleResult(false));
      cancelBtn.addEventListener('click', () => handleResult(false));
      confirmBtn.addEventListener('click', () => handleResult(true));
      
      // ESC键取消
      const escHandler = (e) => {
        if (e.key === 'Escape') {
          document.removeEventListener('keydown', escHandler);
          handleResult(false);
        }
      };
      document.addEventListener('keydown', escHandler);
    });
  }
  
  /**
   * HTML转义
   */
  static escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// 全局暴露
window.Toast = Toast;
