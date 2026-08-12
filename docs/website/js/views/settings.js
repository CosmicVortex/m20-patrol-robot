/** System settings view for the test-stage administrator workflow. */
class SettingsView {
  constructor() { this._content = null; }
  async init() {
    this._content = document.querySelector('.content');
    if (!this._content) return;
    this._content.innerHTML = '<section class="view-container"><h2>系统设置</h2><p>正在读取系统配置…</p></section>';
    try {
      const [info, gimbal, video] = await Promise.all([
        window._api.fetchSystemInfo(), window._api.fetchGimbalDeviceInfo(), window._api.fetchVideo(),
      ]);
      this._render({ info, gimbal, video });
    } catch (error) {
      const message = String(error.message || error).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
      this._content.innerHTML = `<section class="view-container"><h2>系统设置</h2><p>配置读取失败：${message}</p><button class="btn-primary" id="settings-retry">重试</button></section>`;
      this._content.querySelector('#settings-retry')?.addEventListener('click', () => this.init());
    }
  }
  destroy() { this._content = null; }
  _render(data) {
    if (!this._content) return;
    const info = data.info || {}; const hosts = info.hosts || info.hos || {};
    const sources = data.video?.sources || {};
    const esc = value => String(value ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const sourceInput = key => `<label>${esc(sources[key]?.label || key)}<input name="${key}" value="${esc(sources[key]?.rtsp_url || '')}" placeholder="RTSP地址"></label>`;
    this._content.innerHTML = `<section class="view-container"><h2>系统设置</h2>
      <div class="monitor-grid"><section class="card"><h3>运行状态</h3><dl><dt>部署站点</dt><dd>中升之星奔驰</dd><dt>服务</dt><dd>${esc(info.service)}</dd><dt>运行模式</dt><dd>${esc(info.mode)}</dd><dt>控制状态</dt><dd>${info.control_enabled ? '已启用' : '只读'}</dd><dt>AOS</dt><dd>${esc(hosts.aos_host)}:${esc(hosts.aos_port)}</dd><dt>NOS</dt><dd>${esc(hosts.nos_host)}</dd><dt>GOS</dt><dd>${esc(hosts.gos_host)}</dd><dt>云台</dt><dd>${data.gimbal?.connected ? '已连接' : '未连接（云端无法现场连接）'}</dd></dl></section>
      <section class="card"><h3>视频源配置</h3><p>仅保存现场 RTSP 配置；浏览器播放需要后端 playback_url。</p><form id="settings-video-form">${sourceInput('front')}${sourceInput('rear')}${sourceInput('thermal')}${sourceInput('body_front')}<button class="btn-primary">保存视频配置</button></form><div id="settings-message"></div></section>
      <section class="card"><h3>管理员密码</h3><p>测试阶段默认管理员执行全部操作。</p><form id="settings-password-form"><input name="old_password" type="password" placeholder="当前密码" required><input name="new_password" type="password" placeholder="新密码（至少12位）" required><button class="btn-primary">修改密码</button></form><div id="password-message"></div></section></div></section>`;
    this._content.querySelector('#settings-video-form').addEventListener('submit', async event => { event.preventDefault(); const form = new FormData(event.currentTarget); const values = {}; const invalid = []; ['front','rear','thermal','body_front'].forEach(key => { const value = String(form.get(key) || '').trim(); if (value && !value.startsWith('rtsp://')) invalid.push(key); values[key] = { rtsp_url: value }; }); const message = this._content.querySelector('#settings-message'); if (invalid.length) { message.textContent = `RTSP 地址格式错误：${invalid.join('、')}`; return; } try { const result = await window._api.updateVideoConfig(values); const failed = Object.entries(result.results || {}).filter(([, item]) => !item.success); message.textContent = failed.length ? `部分配置失败：${failed.map(([key, item]) => `${key} ${item.error || ''}`).join('；')}` : '视频配置已保存'; } catch (error) { message.textContent = `保存失败：${error.message}`; } });
    this._content.querySelector('#settings-password-form').addEventListener('submit', async event => { event.preventDefault(); const form = new FormData(event.currentTarget); try { await window._api.changePassword(form.get('old_password'), form.get('new_password')); this._content.querySelector('#password-message').textContent = '密码已修改，请重新登录'; window._ws.disconnect(); await window._state.logout(); document.getElementById('login-overlay').style.display = 'flex'; document.getElementById('main-app').style.display = 'none'; } catch (error) { this._content.querySelector('#password-message').textContent = `修改失败：${error.message}`; } });
  }
}
if (typeof module !== 'undefined' && module.exports) module.exports = { SettingsView };
