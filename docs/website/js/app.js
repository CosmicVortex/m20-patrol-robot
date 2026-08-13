/**
 * M20 Pro 巡检机器狗管理平台 - 主应用入口
 * 
 * 功能：
 * - 初始化所有服务（状态管理、API、WebSocket、路由）
 * - 登录/登出处理
 * - 视图路由管理
 * - 紧急停止控制
 * - 云台连接管理
 */

(function() {
  'use strict';
  
  // ── 全局初始化 ──────────────────────────────────────────────────────────────
  window._state = new StateManager();
  window._api = new ApiService(window._state);
  window._ws = new WebSocketService(window._state);
  window._router = new ViewRouter(window._state);

  // ── 键盘快捷键 ──────────────────────────────────────────────────────────────
  document.addEventListener('keydown', (e) => {
    // Esc - 取消/关闭弹窗
    if (e.key === 'Escape') {
      const confirmDialog = document.querySelector('.toast-confirm');
      if (confirmDialog) {
        confirmDialog.classList.add('toast-confirm-hide');
        setTimeout(() => confirmDialog.remove(), 300);
      }
    }
    // Ctrl+Shift+E - 紧急停止
    if (e.ctrlKey && e.shiftKey && e.key === 'E') {
      e.preventDefault();
      if (window.handleEmergencyStop) {
        window.handleEmergencyStop();
      }
    }
    // Ctrl+Shift+S - 导航授权
    if (e.ctrlKey && e.shiftKey && e.key === 'S') {
      e.preventDefault();
      if (window.authorizeNavigation) {
        window.authorizeNavigation();
      }
    }
    // Ctrl+D - 切换到实时监控
    if (e.ctrlKey && e.key === 'd') {
      e.preventDefault();
      window._router?.navigate('dashboard');
    }
    // Ctrl+P - 切换到巡逻管理
    if (e.ctrlKey && e.key === 'p') {
      e.preventDefault();
      window._router?.navigate('patrol');
    }
  });

  // ── 注册视图 ────────────────────────────────────────────────────────────────
  window._router.register('dashboard', new DashboardView());
  window._router.register('patrol', new PatrolView());
  window._router.register('devices', new DevicesView());
  window._router.register('reports', new ReportsView());
  window._router.register('settings', new SettingsView());
  
  // ── 登录/登出处理 ───────────────────────────────────────────────────────────
  document.getElementById('login-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const errEl = document.getElementById('login-error');
    
    errEl.textContent = '';
    
    try {
      const user = await window._state.login(username, password);
      showApp();
      initWebSocket();
      window._router.init();
    } catch (e) {
      errEl.textContent = e.message || '登录失败';
    }
    return false;
  });
  
  document.getElementById('logout-btn')?.addEventListener('click', async function() {
    window._ws.disconnect();
    await window._state.logout();
    showLogin();
  });
  
  // ── 视图切换 ────────────────────────────────────────────────────────────────
  document.querySelectorAll('.nav button[data-view]').forEach(btn => {
    btn.addEventListener('click', () => {
      window._router.navigate(btn.dataset.view);
    });
  });
  
  // ── 辅助函数 ────────────────────────────────────────────────────────────────
  function showLogin() {
    document.getElementById('login-overlay').style.display = 'flex';
    document.getElementById('main-app').style.display = 'none';
  }
  
  function showApp() {
    document.getElementById('login-overlay').style.display = 'none';
    document.getElementById('main-app').style.display = '';
    
    // 更新用户信息
    const user = window._state.get('user');
    if (user) {
      const userEl = document.querySelector('.user span');
      const avatarEl = document.querySelector('.avatar');
      if (userEl) userEl.textContent = user.username;
      if (avatarEl) avatarEl.textContent = user.username[0];
    }
  }
  
  function initWebSocket() {
    window._ws.connectVideo();
    window._ws.connectNav();
  }
  
  // ── 全局暴露的函数（供HTML内联事件调用）────────────────────────────────────
  window.handleLogin = async function(e) {
    e.preventDefault();
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const errEl = document.getElementById('login-error');
    
    errEl.textContent = '';
    
    try {
      const user = await window._state.login(username, password);
      showApp();
      initWebSocket();
      window._router.init();
    } catch (e) {
      errEl.textContent = e.message || '登录失败';
    }
    return false;
  };
  
  window.handleLogout = async function() {
    window._ws.disconnect();
    await window._state.logout();
    showLogin();
  };
  
  // ── 紧急停止 ────────────────────────────────────────────────────────────────
  window.handleEmergencyStop = async function() {
    const confirmed = await Toast.confirm('确认执行紧急停止？此操作将立即停止机器狗所有运动。');
    if (!confirmed) return;
    
    try {
      const result = await window._api.emergencyStop();
      if (!result.command_sent) {
        throw new Error(result.message || '服务端未确认指令发送');
      }
      Toast.success('紧急停止指令已发送');
    } catch (e) {
      Toast.error('操作失败: ' + e.message);
    }
  };
  
  // ── 云台管理 ────────────────────────────────────────────────────────────────
  window.showGimbalModal = function() {
    document.getElementById('gimbal-modal').classList.add('active');
  };
  
  window.hideGimbalModal = function() {
    document.getElementById('gimbal-modal').classList.remove('active');
  };
  
  window.connectGimbal = async function() {
    const host = document.getElementById('gimbal-host').value.trim();
    const username = document.getElementById('gimbal-username').value.trim();
    const password = document.getElementById('gimbal-password').value;
    const errEl = document.getElementById('gimbal-modal-error');
    
    errEl.textContent = '';
    
    try {
      await window._api.connectGimbal(host, username, password);
      hideGimbalModal();
      Toast.success('云台连接成功');
    } catch (e) {
      errEl.textContent = e.message;
    }
  };
  
  window.scanGimbal = async function() {
    try {
      const result = await window._api.scanGimbal();
      Toast.success(`扫描完成，找到 ${result.hosts?.length || 0} 个设备`);
    } catch (e) {
      Toast.error('扫描失败: ' + e.message);
    }
  };
  
  // ── 视频配置 ────────────────────────────────────────────────────────────────
  window.showVideoConfigModal = function() {
    document.getElementById('video-config-modal').classList.add('active');
  };
  
  window.hideVideoConfigModal = function() {
    document.getElementById('video-config-modal').classList.remove('active');
  };
  
  window.saveVideoConfig = async function() {
    const sources = {
      front: { rtsp_url: document.getElementById('rtsp-front').value.trim() },
      rear: { rtsp_url: document.getElementById('rtsp-rear').value.trim() },
      thermal: { rtsp_url: document.getElementById('rtsp-thermal').value.trim() },
      body_front: { rtsp_url: document.getElementById('rtsp-body_front').value.trim() }
    };
    
    const errorEl = document.getElementById('video-config-error');
    const submitBtn = document.getElementById('video-config-submit');
    
    errorEl.textContent = '';
    submitBtn.disabled = true;
    submitBtn.textContent = '保存中...';
    
    try {
      const result = await window._api.updateVideoConfig(sources);
      const failed = Object.entries(result.results || {}).filter(([, item]) => !item.success);
      if (failed.length) {
        throw new Error(failed.map(([key, item]) => `${key}: ${item.error || '配置失败'}`).join('；'));
      }
      hideVideoConfigModal();
      await window._api.fetchVideo();
    } catch (e) {
      errorEl.textContent = '保存失败: ' + e.message;
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = '保存';
    }
  };
  
  // ── 视频控制 ────────────────────────────────────────────────────────────────
  window.toggleFullscreen = function(cameraId) {
    const video = document.getElementById('video-' + cameraId);
    if (!video) return;
    
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      video.requestFullscreen().catch(e => console.error('Fullscreen error:', e));
    }
  };
  
  window.captureFrame = function(cameraId) {
    const video = document.getElementById('video-' + cameraId);
    if (!video || !video.videoWidth) {
      Toast.error('视频未连接，无法截图');
      return;
    }
    
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    
    const link = document.createElement('a');
    link.download = `capture-${cameraId}-${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  };
  
  // ── 导航控制 ────────────────────────────────────────────────────────────────
  window.authorizeNavigation = async function() {
    try {
      await window._api.authorizeNavigation();
      Toast.success('导航授权成功');
      await window._api.fetchNavStatus();
    } catch (e) {
      Toast.error('授权失败: ' + e.message);
    }
  };
  
  window.deauthorizeNavigation = async function() {
    try {
      await window._api.deauthorizeNavigation();
      Toast.info('导航授权已撤销');
      await window._api.fetchNavStatus();
    } catch (e) {
      Toast.error('撤销失败: ' + e.message);
    }
  };
  
  // 初始化完成
  console.log('M20 Pro 巡检平台已初始化');
})();