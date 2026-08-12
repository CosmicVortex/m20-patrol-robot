/**
 * DashboardView - Main monitoring dashboard view
 * Displays telemetry, video wall, map, and controls
 */
class DashboardView {
  constructor() {
    this._pollInterval = null;
    this._clockInterval = null;
  }

  _escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  
  async init() {
    // Start polling for real-time data
    this._startPolling();
    this._startClock();
    
    // Initialize components
    this._initMetrics();
    this._initCameraWall();
    this._initMap();
    this._initControls();
    this._initTimeline();
    
    // Initial data fetch
    await this._fetchInitialData();
  }
  
  destroy() {
    if (this._pollInterval) clearInterval(this._pollInterval);
    if (this._clockInterval) clearInterval(this._clockInterval);
  }
  
  render() {
    // View is already in DOM, just update content
    this._updateDashboard();
  }
  
  /**
   * Start data polling
   */
  _startPolling() {
    // Poll telemetry every 2 seconds; the backend owns the real-data cadence.
    this._pollInterval = setInterval(() => {
      this._fetchStatus();
    }, 2000);
  }
  
  /**
   * Start clock
   */
  _startClock() {
    const updateClock = () => {
      const el = document.getElementById('clock');
      if (el) {
        const d = new Date();
        el.textContent = d.toLocaleString('zh-CN', {
          year: 'numeric', month: '2-digit', day: '2-digit',
          hour: '2-digit', minute: '2-digit', second: '2-digit',
          hour12: false
        });
      }
    };
    updateClock();
    this._clockInterval = setInterval(updateClock, 1000);
  }
  
  /**
   * Fetch initial data
   */
  async _fetchInitialData() {
    try {
      await this._fetchStatus();
      await this._fetchVideo();
      await this._fetchNavStatus();
      await this._fetchWorkOrders();
    } catch (e) {
      console.error('Initial data fetch error:', e);
    }
  }
  
  /**
   * Fetch status
   */
  async _fetchStatus() {
    try {
      await window._api.fetchStatus();
      this._updateDashboard();
    } catch (e) {
      console.log('Status fetch error:', e);
    }
  }
  
  /**
   * Fetch video status
   */
  async _fetchVideo() {
    try {
      await window._api.fetchVideo();
      this._updateVideoWall();
    } catch (e) {
      console.log('Video fetch error:', e);
    }
  }
  
  /**
   * Fetch navigation status
   */
  async _fetchNavStatus() {
    try {
      const data = await window._api.fetchNavStatus();
      this._updateEmergencyBtn(data);
    } catch (e) {
      console.log('Nav status fetch error:', e);
    }
  }

  async _fetchWorkOrders() {
    try {
      await window._api.fetchWorkOrders();
      this._updateMetrics(window._state.get('robot') || {});
    } catch (e) {
      console.log('Work order fetch error:', e);
    }
  }
  
  /**
   * Update dashboard content
   */
  _updateDashboard() {
    const state = window._state;
    if (!state) return;
    
    const robot = state.get('robot') || {};
    const nav = state.get('navigation') || {};
    const video = state.get('video') || {};
    
    // Connection badge
    const badge = document.getElementById('conn-badge');
    if (badge) {
      if (robot.source === 'REAL' && robot.connected) {
        badge.className = 'status-badge ok';
        badge.textContent = 'REAL / CONTROL OFF';
      } else if (robot.source === 'REAL') {
        badge.className = 'status-badge warn';
        badge.textContent = 'REAL / RECONNECTING';
      } else if (robot.source === 'NO_DATA') {
        badge.className = 'status-badge';
        badge.textContent = 'NO DATA / WAITING';
      } else {
        badge.className = 'status-badge';
        badge.textContent = 'UNAVAILABLE';
      }
    }
    
    // Metrics
    this._updateMetrics(robot);
    
    // Robot info panel
    this._updateRobotPanel(robot, nav);
    
    // Emergency button
    this._updateEmergencyBtn(nav);
    
    // Alert count
    const alertEl = document.getElementById('alert-count');
    if (alertEl) {
      const count = robot.errors?.length || 0;
      alertEl.textContent = `告警: ${count}`;
      alertEl.className = 'status-badge' + (count > 0 ? ' blocked' : ' ok');
    }
  }
  
  /**
   * Update metrics cards
   */
  _updateMetrics(robot) {
    // Robot status
    const robotStatus = document.getElementById('robot-status');
    if (robotStatus) {
      const motionMap = {0:'静止',1:'站立',2:'行走',3:'慢跑',4:'上下楼',5:'摔倒'};
      robotStatus.textContent = motionMap[robot.motion_state] || '未知';
    }
    
    // Battery
    const batteryEl = document.getElementById('battery-pct');
    if (batteryEl) {
      const batt = robot.battery;
      batteryEl.textContent = batt == null ? '—' : `${batt}%`;
      batteryEl.style.color = batt == null ? 'var(--color-text-muted)' : batt < 20 ? 'var(--color-error)' : batt < 40 ? 'var(--color-warning)' : 'var(--color-success)';
    }
    
    // Speed
    const speedEl = document.getElementById('speed-state');
    if (speedEl) {
      const speed = robot.speed ?? 0;
      speedEl.textContent = speed > 0.01 ? `${speed.toFixed(2)} m/s` : '—';
    }
    
    // Nav status
    const navStateEl = document.getElementById('nav-state');
    if (navStateEl) {
      const navMap = {0:'待命',1:'导航中',2:'已到达',3:'异常',4:'取消'};
      navStateEl.textContent = navMap[robot.nav_status] || '—';
    }
    
    // Coverage
    const coverageEl = document.getElementById('coverage-rate');
    if (coverageEl) {
      coverageEl.textContent = robot.coverage_rate == null ? '—' : `${robot.coverage_rate.toFixed(1)}%`;
    }
    
    // Work orders
    const workOrdersEl = document.getElementById('work-orders');
    if (workOrdersEl) {
      const orders = window._state.get('workOrders') || [];
      workOrdersEl.textContent = orders.length ? orders.filter(order => order.status !== 'completed').length : '—';
    }
  }
  
  /**
   * Update robot info panel
   */
  _updateRobotPanel(robot, nav) {
    // Position
    const posEl = document.getElementById('robot-pos');
    if (posEl) {
      const x = robot.position?.pos_x ?? 0;
      const y = robot.position?.pos_y ?? 0;
      posEl.textContent = (x || y) ? `${x.toFixed(2)}, ${y.toFixed(2)}` : '—';
    }
    
    // Location
    const locEl = document.getElementById('robot-location');
    if (locEl) {
      locEl.textContent = robot.location || '—';
    }
    
    // Total distance
    const distEl = document.getElementById('total-dist');
    if (distEl) {
      distEl.textContent = (robot.total_distance ?? 0).toFixed(1);
    }
    
    // Loop count
    const lapsEl = document.getElementById('laps-count');
    if (lapsEl) {
      lapsEl.textContent = robot.loop_count ?? 0;
    }
  }
  
  /**
   * Update emergency stop button
   */
  _updateEmergencyBtn(nav) {
    const btn = document.getElementById('emergency-btn');
    if (!btn) return;
    
    const authorized = nav?.authorized && nav?.control_enabled;
    btn.disabled = !authorized;
    const controlIds = ['nav-deauthorize-btn', 'motion-stand-btn', 'motion-lie-btn', 'motion-estop-btn'];
    controlIds.forEach(id => { const control = document.getElementById(id); if (control) control.disabled = !authorized; });
    btn.innerHTML = authorized 
      ? '⚠ 紧急停止<br><small>点击立即停止</small>'
      : '⚠ 紧急停止<br><small>需授权后启用</small>';
  }
  
  /**
   * Update camera wall
   */
  _updateVideoWall() {
    const state = window._state;
    if (!state) return;
    
    const video = state.get('video') || {};
    const sources = video.sources || {};
    
    const cameras = document.querySelectorAll('#camera-wall .camera');
    const keys = ['front', 'thermal', 'body_front', 'rear'];
    
    cameras.forEach((cam, i) => {
      const key = keys[i];
      const src = sources[key] || {};
      const stateEl = cam.querySelector('.camera-status');
      const videoEl = cam.querySelector('.camera-video');
      const tools = cam.querySelectorAll('.camera-controls button');
      
      if (!stateEl) return;

      const videoAction = async action => {
        try {
          const result = await window._api[action](key);
          stateEl.textContent = result.error || result.status || '操作完成';
          await window._api.fetchVideo();
          this._updateVideoWall();
        } catch (error) { stateEl.textContent = `视频操作失败：${error.message}`; }
      };
      tools.forEach(button => {
        if (!button.dataset.videoAction) return;
        if (!button.dataset.videoActionBound) {
          button.dataset.videoActionBound = '1';
          button.addEventListener('click', () => videoAction(button.dataset.videoAction));
        }
      });
      
      if (src.playback_url) {
        stateEl.className = 'camera-status online';
        stateEl.innerHTML = '<strong>READY</strong>浏览器转码流';
        cam.classList.add('connected');
        cam.classList.remove('unverified');
        if (videoEl) {
          videoEl.src = src.playback_url;
          videoEl.classList.add('active');
        }
        tools.forEach(btn => {
          if (btn.dataset.videoAction === 'probe' || btn.dataset.videoAction === 'start') btn.disabled = false;
          else btn.disabled = !src.playback_url;
        });
      } else if (src.state === 'blocked') {
        stateEl.className = 'media-state blocked';
        stateEl.innerHTML = `<strong>BLOCKED</strong>${this._escapeHtml(src.note || '视频流已禁用')}`;
        cam.classList.remove('connected');
        cam.classList.add('unverified');
        if (videoEl) videoEl.classList.remove('active');
        tools.forEach(btn => btn.disabled = true);
      } else {
        stateEl.className = 'media-state unverified';
        stateEl.innerHTML = `<strong>UNVERIFIED</strong>${this._escapeHtml(src.note || '待配置')}`;
        cam.classList.remove('connected');
        cam.classList.add('unverified');
        if (videoEl) videoEl.classList.remove('active');
        tools.forEach(btn => btn.disabled = true);
      }
    });
  }
  
  /**
   * Initialize metrics section
   */
  _initMetrics() {
    // Metrics are static HTML, no initialization needed
  }
  
  /**
   * Initialize camera wall
   */
  _initCameraWall() {
    // Camera wall is static HTML, video sources will be set dynamically
  }
  
  /**
   * Initialize map
   */
  _initMap() {
    // Map will be initialized when needed
    window._mapInitialized = false;
  }
  
  /**
   * Initialize controls
   */
  _initControls() {
    // Controls are static HTML, will be enabled/disabled based on state
  }
  
  /**
   * Initialize timeline
   */
  _initTimeline() {
    // Timeline will be updated with real data
  }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { DashboardView };
}
