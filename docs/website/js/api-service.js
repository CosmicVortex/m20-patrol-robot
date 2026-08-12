/**
 * ApiService - Centralized API client for M20 Pro patrol system
 * Wraps all HTTP requests with auth headers and error handling
 */
class ApiService {
  constructor(stateManager) {
    this.state = stateManager;
    this._baseUrl = '/api/v1';
  }
  
  /**
   * Get auth headers if logged in
   */
  _getHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    const token = this.state.get('token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }
  
  /**
   * Make GET request
   */
  async get(endpoint) {
    const resp = await fetch(`${this._baseUrl}${endpoint}`, {
      headers: this._getHeaders(),
    });
    return this._handleResponse(resp);
  }
  
  /**
   * Make POST request
   */
  async post(endpoint, body) {
    const resp = await fetch(`${this._baseUrl}${endpoint}`, {
      method: 'POST',
      headers: this._getHeaders(),
      body: JSON.stringify(body),
    });
    return this._handleResponse(resp);
  }
  
  /**
   * Make PUT request
   */
  async put(endpoint, body) {
    const resp = await fetch(`${this._baseUrl}${endpoint}`, {
      method: 'PUT',
      headers: this._getHeaders(),
      body: JSON.stringify(body),
    });
    return this._handleResponse(resp);
  }
  
  /**
   * Make DELETE request
   */
  async delete(endpoint) {
    const resp = await fetch(`${this._baseUrl}${endpoint}`, {
      method: 'DELETE',
      headers: this._getHeaders(),
    });
    return this._handleResponse(resp);
  }
  
  /**
   * Handle API response
   */
  async _handleResponse(resp) {
    const data = await resp.json();
    
    if (!resp.ok) {
      // Handle auth errors
      if (resp.status === 401) {
        this.state.set('isAuthenticated', false);
        window.location.href = '/';
        throw new Error('会话已过期，请重新登录');
      }
      throw new Error(data.error || data.message || `API 错误: ${resp.status}`);
    }

    if (data && data.status === 'success' && Object.prototype.hasOwnProperty.call(data, 'data')) {
      return data.data;
    }
    return data;
  }
  
  // ── Telemetry ────────────────────────────────────────────────────────────
  
  async fetchStatus() {
    const data = await this.get('/status/latest');
    this.state.updateTelemetry(data);
    return data;
  }
  
  async fetchHealth() {
    return this.get('/health');
  }
  
  // ── Navigation ───────────────────────────────────────────────────────────
  
  async fetchNavStatus() {
    const data = await this.get('/navigation/status');
    this.state.updateNavigation(data);
    return data;
  }
  
  async authorizeNavigation() {
    return this.post('/navigation/authorize', {});
  }
  
  async cancelNavigation() {
    return this.post('/navigation/cancel', {});
  }
  
  async createTask(params) {
    return this.post('/navigation/tasks', params);
  }

  async sendNavigation(params) { return this.post('/navigation/tasks', params); }
  
  // ── Motion Control ───────────────────────────────────────────────────────
  
  async emergencyStop() {
    return this.post('/emergency/stop', {});
  }
  
  async motionState(state) {
    return this.post('/motion/state', { state });
  }
  
  async gaitSwitch(gait) {
    return this.post('/motion/gait', { gait });
  }
  
  async axisControl(x, y, yaw) { return this.post('/motion/axis', { x, y, yaw }); }
  async lightControl(front, back = front) { return this.post('/motion/light', { front, back }); }
  async modeSwitch(mode) { return this.post('/motion/mode', { mode }); }
  async sleepMode(sleep, auto = false, time = 10) { return this.post('/motion/sleep', { sleep, auto, time }); }
  
  async chargeControl(action) {
    return this.post('/motion/charge', { charge: action });
  }

  async fetchMotionStatus() { return this.get('/motion/status'); }
  async authorizeMotion() { return this.post('/motion/authorize', {}); }
  async deauthorizeMotion() { return this.post('/motion/deauthorize', {}); }
  async deauthorizeNavigation() { return this.post('/navigation/deauthorize', {}); }

  
  // ── Video ────────────────────────────────────────────────────────────────
  
  async fetchVideo() {
    const data = await this.get('/video');
    this.state.updateVideo(data);
    return data;
  }
  
  async updateVideoConfig(sources) {
    return this.post('/video/config', { sources });
  }

  async probeVideo(source) { return this.post('/video/probe', { source }); }
  async startVideo(source) { return this.post('/video/start', { source }); }
  async stopVideo(source) { return this.post('/video/stop', { source }); }
  
  // ── Gimbal ───────────────────────────────────────────────────────────────
  
  async fetchGimbalState() {
    return this.get('/gimbal/state');
  }
  
  async connectGimbal(host, username, password) {
    return this.post('/gimbal/connect', { host, username, password });
  }
  
  async scanGimbal() {
    return this.get('/gimbal/scan');
  }
  
  async moveGimbal(direction) {
    return this.post('/gimbal/move', { direction });
  }
  
  async zoomGimbal(factor) {
    return this.post('/gimbal/zoom', { level: factor });
  }

  async angleGimbal(pan, tilt) { return this.post('/gimbal/angle', { pan, tilt }); }
  
  // ── Work Orders ──────────────────────────────────────────────────────────
  
  async fetchWorkOrders() {
    const data = await this.get('/work-orders');
    this.state.updateWorkOrders(data);
    return data;
  }
  
  async createWorkOrder(params) {
    return this.post('/work-orders', params);
  }
  
  async updateWorkOrder(id, params) {
    return this.put(`/work-orders/${id}`, params);
  }
  
  // ── Inspection Points ────────────────────────────────────────────────────
  
  async fetchInspectionPoints() {
    return this.get('/inspection-points');
  }

  async fetchTimeline() {
    return this.get('/timeline');
  }
  
  // ── Users ────────────────────────────────────────────────────────────────
  
  async fetchUsers() {
    return this.get('/users');
  }
  
  async changePassword(oldPassword, newPassword) {
    return this.post('/users/password', { old_password: oldPassword, new_password: newPassword });
  }
  
  // ── System Info ──────────────────────────────────────────────────────────
  
  async fetchSystemInfo() {
    return this.get('/system/info');
  }

  async fetchGimbalDeviceInfo() {
    return this.get('/gimbal/device/info');
  }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { ApiService };
}
