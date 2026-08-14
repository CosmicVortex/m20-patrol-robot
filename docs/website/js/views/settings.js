/**
 * SettingsView - 系统设置视图
 * 
 * 功能：
 * - 运行状态显示
 * - 视频源配置
 * - 密码修改
 * - 系统信息
 */
class SettingsView {
  constructor() {
    this._content = null;
  }
  
  async init() {
    this._content = document.querySelector('#view-settings');
    if (!this._content) return;
    
    await this._loadSettings();
  }
  
  destroy() {
    this._content = null;
  }
  
  render() {
    this._loadSettings();
  }

  async _loadSettings() {
    try {
      const [info, gimbal, video] = await Promise.all([
        window._api.fetchSystemInfo(),
        window._api.fetchGimbalDeviceInfo(),
        window._api.fetchVideo()
      ]);
      this._render({ info, gimbal, video });
    } catch (error) {
      // 显示友好的错误信息，而不是告警
      const errorMsg = error?.message || '未知错误';
      this._content.innerHTML = `
        <div class="card" style="padding:var(--space-8);text-align:center;">
          <div style="font-size:48px;margin-bottom:var(--space-4)">⚠️</div>
          <h3>配置加载失败</h3>
          <p style="color:var(--color-text-muted);margin-bottom:var(--space-4)">${this._escapeHtml(errorMsg)}</p>
          <button class="btn btn-primary" onclick="window._router.refresh()">重新加载</button>
        </div>
      `;
    }
  }

  _render(data) {
    if (!this._content) return;
    
    const info = data.info || {};
    const hosts = info.hosts || info.hos || {};
    const sources = data.video?.sources || {};
    const esc = value => String(value ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    
    const sourceInput = key => `
      <div class="form-group">
        <label for="rtsp-${key}">${esc(sources[key]?.label || key)}</label>
        <input type="text" id="rtsp-${key}" name="${key}" class="input" value="${esc(sources[key]?.rtsp_url || '')}" placeholder="RTSP地址（可选）">
      </div>
    `;
    
    this._content.innerHTML = `
      <h2>系统设置</h2>
      <div class="monitor-grid">
        <div class="card">
          <h3>运行状态</h3>
          <dl style="display:grid;grid-template-columns:repeat(2,1fr);gap:var(--space-3)">
            <dt style="color:var(--color-text-muted);font-size:var(--fs-xs);text-transform:uppercase">部署站点</dt>
            <dd style="font-weight:500">中升之星奔驰</dd>
            
            <dt style="color:var(--color-text-muted);font-size:var(--fs-xs);text-transform:uppercase">服务</dt>
            <dd>${esc(info.service)}</dd>
            
            <dt style="color:var(--color-text-muted);font-size:var(--fs-xs);text-transform:uppercase">运行模式</dt>
            <dd>${esc(info.mode)}</dd>
            
            <dt style="color:var(--color-text-muted);font-size:var(--fs-xs);text-transform:uppercase">控制状态</dt>
            <dd>${info.control_enabled ? '<span class="status-badge ok">已启用</span>' : '<span class="status-badge warn">只读</span>'}</dd>
            
            <dt style="color:var(--color-text-muted);font-size:var(--fs-xs);text-transform:uppercase">AOS</dt>
            <dd>${esc(hosts.aos_host)}:${esc(hosts.aos_port)}</dd>
            
            <dt style="color:var(--color-text-muted);font-size:var(--fs-xs);text-transform:uppercase">NOS</dt>
            <dd>${esc(hosts.nos_host)}</dd>
            
            <dt style="color:var(--color-text-muted);font-size:var(--fs-xs);text-transform:uppercase">GOS</dt>
            <dd>${esc(hosts.gos_host)}</dd>
            
            <dt style="color:var(--color-text-muted);font-size:var(--fs-xs);text-transform:uppercase">云台</dt>
            <dd>${data.gimbal?.connected ? '<span class="status-badge ok">已连接</span>' : '<span class="status-badge blocked">未连接（云端无法现场连接）</span>'}</dd>
          </dl>
        </div>
        
        <div class="card">
          <h3>视频源配置</h3>
          <p style="font-size:var(--fs-xs);color:var(--color-text-muted);margin-bottom:var(--space-4)">仅保存现场RTSP配置；浏览器播放需要后端playback_url。</p>
          <form id="settings-video-form">
            ${sourceInput('front')}
            ${sourceInput('rear')}
            ${sourceInput('thermal')}
            ${sourceInput('body_front')}
            <button type="submit" class="btn btn-primary">保存视频配置</button>
          </form>
          <div id="settings-message" style="margin-top:var(--space-3);font-size:var(--fs-sm)"></div>
        </div>
      </div>
      
      <div class="card" style="margin-top:var(--space-4)">
        <h3>管理员密码</h3>
        <p style="font-size:var(--fs-xs);color:var(--color-text-muted);margin-bottom:var(--space-4)">测试阶段默认管理员执行全部操作。</p>
        <form id="settings-password-form">
          <div class="form-row">
            <div class="form-group">
              <label for="old-password">当前密码</label>
              <input type="password" id="old-password" name="old_password" class="input" placeholder="当前密码" required>
            </div>
            <div class="form-group">
              <label for="new-password">新密码</label>
              <input type="password" id="new-password" name="new_password" class="input" placeholder="新密码（至少6位）" required>
            </div>
          </div>
          <button type="submit" class="btn btn-primary">修改密码</button>
        </form>
        <div id="password-message" style="margin-top:var(--space-3);font-size:var(--fs-sm)"></div>
      </div>
      
      <div class="card" style="margin-top:var(--space-4)">
        <h3>系统信息</h3>
        <dl style="display:grid;grid-template-columns:repeat(3,1fr);gap:var(--space-3)">
          <dt style="color:var(--color-text-muted);font-size:var(--fs-xs);text-transform:uppercase">Python版本</dt>
          <dd id="setting-python-version">待配置</dd>

          <dt style="color:var(--color-text-muted);font-size:var(--fs-xs);text-transform:uppercase">固件版本</dt>
          <dd id="setting-firmware-version">待配置</dd>

          <dt style="color:var(--color-text-muted);font-size:var(--fs-xs);text-transform:uppercase">协议版本</dt>
          <dd id="setting-protocol-version">待配置</dd>

          <dt style="color:var(--color-text-muted);font-size:var(--fs-xs);text-transform:uppercase">云台型号</dt>
          <dd>SR-UPA810T609</dd>

          <dt style="color:var(--color-text-muted);font-size:var(--fs-xs);text-transform:uppercase">部署时间</dt>
          <dd>${new Date().toLocaleDateString('zh-CN')}</dd>
        </dl>
      </div>
    `;
    
    // 绑定视频配置表单
    this._content.querySelector('#settings-video-form')?.addEventListener('submit', async event => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const values = {};
      const invalid = [];
      const submitBtn = event.currentTarget.querySelector('button[type="submit"]');
      const originalText = submitBtn?.textContent || '保存';
      
      ['front','rear','thermal','body_front'].forEach(key => {
        const value = String(form.get(key) || '').trim();
        // 允许空地址，只检查非空值是否以rtsp://开头
        if (value && !value.startsWith('rtsp://')) invalid.push(key);
        values[key] = { rtsp_url: value };
      });
      
      const message = this._content.querySelector('#settings-message');
      if (invalid.length) {
        message.textContent = `RTSP地址格式错误：${invalid.join('、')}`;
        message.style.color = 'var(--color-error)';
        return;
      }
      
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = '保存中...';
      }
      
      try {
        const result = await window._api.updateVideoConfig(values);
        const failed = Object.entries(result.results || {}).filter(([, item]) => !item.success);
        message.textContent = failed.length 
          ? `部分配置失败：${failed.map(([key, item]) => `${key} ${item.error || ''}`).join('；')}`
          : '视频配置已保存';
        message.style.color = failed.length ? 'var(--color-warning)' : 'var(--color-success)';
        if (!failed.length && Toast) Toast.success('视频配置已保存');
      } catch (error) {
        message.textContent = `保存失败：${error.message}`;
        message.style.color = 'var(--color-error)';
        if (Toast) Toast.error(`保存失败：${error.message}`);
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        }
      }
    });
    
    // 绑定密码修改表单
    this._content.querySelector('#settings-password-form')?.addEventListener('submit', async event => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      const message = this._content.querySelector('#password-message');
      const submitBtn = event.currentTarget.querySelector('button[type="submit"]');
      const originalText = submitBtn?.textContent || '修改密码';
      
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = '修改中...';
      }
      
      try {
        await window._api.changePassword(form.get('old_password'), form.get('new_password'));
        message.textContent = '密码已修改，请重新登录';
        message.style.color = 'var(--color-success)';
        if (Toast) Toast.success('密码已修改，请重新登录');
        
        // 退出登录
        window._ws.disconnect();
        await window._state.logout();
        document.getElementById('login-overlay').style.display = 'flex';
        document.getElementById('main-app').style.display = 'none';
      } catch (error) {
        message.textContent = `修改失败：${error.message}`;
        message.style.color = 'var(--color-error)';
      }
    });
  }

  _escapeHtml(value) {
    return String(value ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
}

if (typeof module !== 'undefined' && module.exports) module.exports = { SettingsView };