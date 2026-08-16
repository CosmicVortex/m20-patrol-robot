/**
 * StateManager - Centralized state management for M20 Pro patrol system
 * Manages robot state, user auth, navigation status, and alerts
 */
class StateManager {
  constructor() {
    this._state = {
      // Auth
      user: null,
      token: null,
      isAuthenticated: false,
      
      // Robot telemetry
      robot: {
        connected: false,
        source: 'NO_DATA',
        battery: null,  // 主电池（取两块中较低值）
        battery_left: null,  // 左电池电量
        battery_right: null,  // 右电池电量
        battery_list: [],  // 电池列表 [{BatteryLevel, Voltage, serial}]
        battery_status: {},  // 电池状态 {BatteryLevelLeft, BatteryLevelRight...}
        motion_state: 0,
        gait: 'flat',
        speed: 0,
        nav_status: 0,
        loop_count: 0,
        total_distance: 0,
        position: { pos_x: 0, pos_y: 0, pos_z: 0 },
        location: null,
        errors: [],
        coverage_rate: 0,
      },
      
      // Navigation
      navigation: {
        authorized: false,
        control_enabled: false,
        task_id: null,
        status: 0,
      },
      
      // Video
      video: {
        sources: {},
        status: 'VIDEO_IO_BLOCKED',
      },
      
      // Alerts
      alerts: [],
      unreadAlerts: 0,
      
      // Work orders
      workOrders: [],

      // Devices
      devices: [],

      // Patrol tasks
      tasks: [],

      // Inspection points
      inspectionPoints: [],

      // UI state
      currentView: 'dashboard',
      sidebarOpen: true,
    };
    
    this._listeners = new Map();
  }
  
  /**
   * Get current state value
   * @param {string} path - Dot notation path (e.g., 'robot.battery')
   */
  get(path) {
    return path.split('.').reduce((obj, key) => obj?.[key], this._state);
  }
  
  /**
   * Set state value with dot notation
   * @param {string} path - Dot notation path
   * @param {*} value - New value
   */
  set(path, value) {
    const keys = path.split('.');
    const last = keys.pop();
    const obj = keys.reduce((o, k) => o[k] = o[k] || {}, this._state);
    obj[last] = value;
    this._notify(path);
  }
  
  /**
   * Merge state object
   * @param {string} path - Dot notation path
   * @param {object} partial - Partial state to merge
   */
  merge(path, partial) {
    const current = this.get(path);
    this.set(path, { ...current, ...partial });
  }
  
  /**
   * Subscribe to state changes
   * @param {string} path - Dot notation path or '*' for all
   * @param {Function} callback - Called with (newValue, oldValue)
   * @returns {Function} Unsubscribe function
   */
  subscribe(path, callback) {
    if (!this._listeners.has(path)) {
      this._listeners.set(path, new Set());
    }
    this._listeners.get(path).add(callback);
    return () => this._listeners.get(path)?.delete(callback);
  }
  
  /**
   * Notify all subscribers
   * @param {string} path - Changed path
   */
  _notify(path) {
    // Notify exact match
    this._listeners.get(path)?.forEach(cb => {
      try { cb(this.get(path)); } catch (e) {}
    });

    // Notify wildcard
    this._listeners.get('*')?.forEach(cb => {
      try { cb(this._state); } catch (e) {}
    });
  }
  
  /**
   * Update from telemetry response
   * @param {object} data - Response from /api/v1/status/latest
   */
  updateTelemetry(data) {
    const d = data.data || {};

    this.set('robot.connected', data.connected);
    this.set('robot.source', data.source);

    // 电池数据 - 支持双电池显示
    const batteryPercent = data.battery_percent != null ? data.battery_percent : null;
    this.set('robot.battery', batteryPercent);

    // 解析电池列表和状态
    const device = d.device || {};
    const batteryList = device.battery_list || [];
    const batteryStatus = device.battery_status || {};

    this.set('robot.battery_list', batteryList);
    this.set('robot.battery_status', batteryStatus);

    // 提取左/右电池电量
    if (batteryList.length >= 2) {
      this.set('robot.battery_left', batteryList[0].BatteryLevel ?? null);
      this.set('robot.battery_right', batteryList[1].BatteryLevel ?? null);
    } else if (batteryStatus.BatteryLevelLeft != null) {
      this.set('robot.battery_left', batteryStatus.BatteryLevelLeft);
      this.set('robot.battery_right', batteryStatus.BatteryLevelRight);
    }

    this.set('robot.motion_state', d.basic?.motion_state ?? 0);
    this.set('robot.gait', d.basic?.gait ?? 'flat');
    this.set('robot.nav_status', d.nav_status?.status ?? 0);
    this.set('robot.loop_count', d.nav_status?.loop_count ?? 0);
    this.set('robot.total_distance', d.nav_status?.total_distance ?? 0);
    this.set('robot.position', d.position || null);
    this.set('robot.location', d.position?.location ?? null);
    this.set('robot.errors', d.errors || []);
    this.set('robot.coverage_rate', data.inspection_stats?.coverage_rate ?? 0);

    // Update motion speed
    const m = d.motion || {};
    const speed = Math.sqrt((m.linear_x || 0) ** 2 + (m.linear_y || 0) ** 2);
    this.set('robot.speed', speed);

    // Update alerts
    const errorCount = (d.errors || []).length;
    this.set('alerts', d.errors || []);
    this.set('unreadAlerts', errorCount);

    this._notify('robot');
  }
  
  /**
   * Update navigation status
   * @param {object} data - Response from /api/v1/navigation/status
   */
  updateNavigation(data) {
    this.set('navigation.authorized', data.authorized ?? false);
    this.set('navigation.control_enabled', data.control_enabled ?? false);
    this.set('navigation.status', data.status ?? 0);
    this._notify('navigation');
  }
  
  /**
   * Update video status
   * @param {object} data - Response from /api/v1/video
   */
  updateVideo(data) {
    this.set('video.sources', data.sources || {});
    this.set('video.status', data.status || 'VIDEO_IO_BLOCKED');
    this._notify('video');
  }
  
  /**
   * Update work orders
   * @param {object} data - Response from /api/v1/work-orders
   */
  updateWorkOrders(data) {
    this.set('workOrders', data.orders || []);
    this._notify('workOrders');
  }

  /**
   * Update devices
   * @param {object} data - Response from /api/v1/devices
   */
  updateDevices(data) {
    this.set('devices', data.devices || data || []);
    this._notify('devices');
  }

  /**
   * Update patrol tasks
   * @param {object} data - Response from /api/v1/navigation/tasks
   */
  updateTasks(data) {
    this.set('tasks', data.tasks || data || []);
    this._notify('tasks');
  }

  /**
   * Update inspection points
   * @param {object} data - Response from /api/v1/inspection-points
   */
  updateInspectionPoints(data) {
    this.set('inspectionPoints', data.points || data || []);
    this._notify('inspectionPoints');
  }
  
  /**
   * Login
   * @param {string} username
   * @param {string} password
   * @returns {Promise<object>} User data
   */
  async login(username, password) {
    const resp = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    
    const data = await resp.json();
    
    if (resp.ok && data.status === 'success' && data.data) {
      const user = data.data;
      this.set('token', null);
      this.set('user', user);
      this.set('isAuthenticated', true);
      return user;
    } else {
      throw new Error(data.error || data.message || '登录失败');
    }
  }
  
  /**
   * Logout
   */
  async logout() {
    fetch('/api/v1/auth/logout', { method: 'POST' }).catch(() => {});
    this.set('token', null);
    this.set('user', null);
    this.set('isAuthenticated', false);
    this.set('currentView', 'dashboard');
  }
  
  /**
   * Check current session
   */
  async checkSession() {
    try {
      const resp = await fetch('/api/v1/auth/me');
      if (resp.ok) {
        const data = await resp.json();
        this.set('user', data.data);
        this.set('isAuthenticated', true);
        return true;
      }
    } catch (e) {
      // Session invalid
    }
    this.set('isAuthenticated', false);
    return false;
  }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { StateManager };
}
