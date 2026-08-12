/**
 * Main Application Entry Point
 * Initializes StateManager, ApiService, WebSocketService, and ViewRouter
 */

(function() {
  'use strict';
  
  // ── Global State ──────────────────────────────────────────────────────────
  window._state = new StateManager();
  window._api = new ApiService(window._state);
  window._ws = new WebSocketService(window._state);
  window._router = new ViewRouter(window._state);
  
  // ── Register Views ────────────────────────────────────────────────────────
  window._router.register('dashboard', new DashboardView());
  window._router.register('patrol', new PatrolView());
  window._router.register('settings', new SettingsView());

  
  // ── Login/Logout Handlers ─────────────────────────────────────────────────
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

  
  // ── View Management ───────────────────────────────────────────────────────
  function showLogin() {
    document.getElementById('login-overlay').style.display = 'flex';
    document.getElementById('main-app').style.display = 'none';
  }
  
  function showApp() {
    document.getElementById('login-overlay').style.display = 'none';
    document.getElementById('main-app').style.display = '';
    
    // Update user info
    const user = window._state.get('user');
    if (user) {
      const userEl = document.querySelector('.user span');
      const avatarEl = document.querySelector('.avatar');
      if (userEl) userEl.textContent = user.username;
      if (avatarEl) avatarEl.textContent = user.username[0];
    }
  }
  
  // ── WebSocket ─────────────────────────────────────────────────────────────
  function initWebSocket() {
    window._ws.connectVideo();
    window._ws.connectNav();
  }
  
  // ── Emergency Stop ────────────────────────────────────────────────────────
  window.handleEmergencyStop = async function() {
    if (!confirm('确认执行紧急停止？')) return;
    
    try {
      const result = await window._api.emergencyStop();
      if (!result.command_sent) {
        throw new Error(result.message || '服务端未确认指令发送');
      }
      alert('紧急停止指令已发送');
    } catch (e) {
      alert('操作失败: ' + e.message);
    }
  };
  
  // ── Gimbal Functions ──────────────────────────────────────────────────────
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
      alert('云台连接成功');
    } catch (e) {
      errEl.textContent = e.message;
    }
  };
  
  window.scanGimbal = async function() {
    try {
      const result = await window._api.scanGimbal();
      alert('扫描完成，找到: ' + (result.hosts?.length || 0) + ' 个设备');
    } catch (e) {
      alert('扫描失败: ' + e.message);
    }
  };
  
  // ── Video Config Functions ────────────────────────────────────────────────
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
  
  // ── Fullscreen & Capture ──────────────────────────────────────────────────
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
      alert('视频未连接，无法截图');
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
  
  // ── Navigation Actions ────────────────────────────────────────────────────
  window.authorizeNavigation = async function() {
    try {
      await window._api.authorizeNavigation();
      alert('导航授权成功');
      await window._api.fetchNavStatus();
    } catch (e) {
      alert('授权失败: ' + e.message);
    }
  };
  
  window.cancelNavigation = async function() {
    if (!confirm('确认取消当前导航任务？')) return;
    try {
      await window._api.cancelNavigation();
      alert('导航已取消');
      await window._api.fetchNavStatus();
    } catch (e) {
      alert('取消失败: ' + e.message);
    }
  };
  
  async function controlAction(action) {
    const message = document.getElementById('control-message');
    try {
      const result = await action();
      if (message) message.textContent = result.message || result.status || '操作完成';
      await window._api.fetchNavStatus();
      updateControlButtons();
    } catch (error) { if (message) message.textContent = `操作失败：${error.message}`; }
  }

  function updateControlButtons() {
    const nav = window._state.get('navigation') || {};
    const enabled = Boolean(nav.control_enabled && nav.authorized);
    ['nav-deauthorize-btn','motion-stand-btn','motion-lie-btn','motion-estop-btn'].forEach(id => {
      const button = document.getElementById(id); if (button) button.disabled = !enabled;
    });
  }

  // ── Map Functions ─────────────────────────────────────────────────────────
  window.updateMap = function(position) {
    // Called by legacy code, will be handled by DashboardView
    const state = window._state;
    if (state) {
      state.merge('robot.position', position);
    }
  };
  
  document.getElementById('login-form')?.addEventListener('submit', window.handleLogin);
  document.getElementById('logout-btn')?.addEventListener('click', window.handleLogout);
  document.getElementById('gimbal-connect-btn')?.addEventListener('click', window.showGimbalModal);
  document.getElementById('gimbal-scan-btn')?.addEventListener('click', window.scanGimbal);
  document.getElementById('video-config-btn')?.addEventListener('click', window.showVideoConfigModal);
  document.getElementById('emergency-btn')?.addEventListener('click', window.handleEmergencyStop);
  document.getElementById('nav-authorize-btn')?.addEventListener('click', () => controlAction(window._api.authorizeNavigation.bind(window._api)));
  document.getElementById('nav-deauthorize-btn')?.addEventListener('click', () => controlAction(window._api.deauthorizeNavigation.bind(window._api)));
  document.getElementById('motion-stand-btn')?.addEventListener('click', () => controlAction(() => window._api.motionState(1)));
  document.getElementById('motion-lie-btn')?.addEventListener('click', () => controlAction(() => window._api.motionState(0)));
  document.getElementById('motion-estop-btn')?.addEventListener('click', () => controlAction(() => window._api.motionState(2)));
  document.querySelectorAll('[data-camera-action="fullscreen"]').forEach(button => {
    button.addEventListener('click', () => window.toggleFullscreen(button.dataset.camera));
  });
  document.querySelectorAll('[data-camera-action="capture"]').forEach(button => {
    button.addEventListener('click', () => window.captureFrame(button.dataset.camera));
  });
  document.getElementById('gimbal-connect-submit')?.addEventListener('click', window.connectGimbal);
  document.getElementById('video-config-submit')?.addEventListener('click', window.saveVideoConfig);

  // ── App Initialization ────────────────────────────────────────────────────
  async function init() {
    // Check existing session
    const isAuthenticated = await window._state.checkSession();
    
    if (isAuthenticated) {
      showApp();
      initWebSocket();
      window._router.init();
    } else {
      showLogin();
    }
  }
  
  // Start the app
  init();
  
})();
