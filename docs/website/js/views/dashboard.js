/**
 * DashboardView - M20 Pro 巡检监控核心视图
 * 
 * 功能：
 * - 实时数据轮询（2秒）
 * - 视频墙管理（4路相机）
 * - 机器人状态面板
 * - 云台控制
 * - 控制面板（授权/急停/回充）
 * - 时间线动态生成
 * - 地图Canvas绘制
 */
class DashboardView {
  constructor() {
    this._pollInterval = null;
    this._clockInterval = null;
    this._authorized = false;
    this._mapAnimFrame = null;
    this._mapPoints = [];
    this._gimbalState = null;
  }

  _escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  
  async init() {
    this._startPolling();
    this._startClock();
    this._initEventListeners();
    this._initMap();
    await this._fetchInitialData();
    // 延迟启动视频：等待数据加载完成后再自动连接
    setTimeout(() => this._autoStartVideo(), 2000);
    // 每30秒检查一次视频连接状态，自动重连
    setInterval(() => this._autoStartVideo(), 30000);
  }
  destroy() {
    if (this._pollInterval) clearInterval(this._pollInterval);
    if (this._clockInterval) clearInterval(this._clockInterval);
    if (this._mapAnimFrame) cancelAnimationFrame(this._mapAnimFrame);
  }
  
  render() {
    this._updateDashboard();
  }

  // ========== 轮询与定时 ==========
  
  _startPolling() {
    this._pollInterval = setInterval(() => this._fetchStatus(), 2000);
  }
  
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

  // ========== 数据获取 ==========
  
  async _fetchInitialData() {
    try {
      await Promise.all([
        this._fetchStatus(),
        this._fetchVideo(),
        this._fetchNavStatus(),
        this._fetchWorkOrders(),
        this._fetchGimbalState()
      ]);
    } catch (e) {
      console.error('Initial data fetch error:', e);
    }
  }
  
  async _fetchStatus() {
    try {
      await window._api.fetchStatus();
      this._updateDashboard();
    } catch (e) {
      console.log('Status fetch error:', e);
    }
  }
  
  async _fetchVideo() {
    try {
      await window._api.fetchVideo();
      this._updateVideoWall();
    } catch (e) {
      console.log('Video fetch error:', e);
    }
  }
  
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

  async _fetchGimbalState() {
    try {
      const data = await window._api.fetchGimbalState();
      this._updateGimbalPanel(data);
    } catch (e) {
      console.log('Gimbal state fetch error:', e);
    }
  }

  // ========== UI更新 ==========
  
  _updateDashboard() {
    const state = window._state;
    if (!state) return;
    
    const robot = state.get('robot') || {};
    const nav = state.get('navigation') || {};
    
    this._updateConnectionBadge(robot);
    this._updateMetrics(robot);
    this._updateRobotPanel(robot, nav);
    this._updateEmergencyBtn(nav);
    this._updateAlertCount(robot);
    this._updateTimeline(robot);
    this._updateMap(robot);
  }

  _updateConnectionBadge(robot) {
    const badge = document.getElementById('conn-badge');
    if (!badge) return;
    
    const source = robot.source || 'NO_DATA';
    const connected = robot.connected || false;
    
    if (source === 'REAL' && connected) {
      badge.className = 'status-badge ok';
      badge.textContent = robot.control_enabled ? 'REAL / CONTROL ON' : 'REAL / CONTROL OFF';
    } else if (source === 'REAL') {
      badge.className = 'status-badge warn';
      badge.textContent = 'REAL / RECONNECTING';
    } else if (source === 'NO_DATA') {
      badge.className = 'status-badge';
      badge.textContent = 'NO DATA / WAITING';
    } else {
      badge.className = 'status-badge';
      badge.textContent = 'UNAVAILABLE';
    }
  }

  _updateMetrics(robot) {
    // 在线机器狗数量
    const robotCountEl = document.getElementById('robot-count');
    const robotStatusEl = document.getElementById('robot-status');
    if (robotCountEl) {
      const connected = robot.connected || false;
      const source = robot.source || 'NO_DATA';
      robotCountEl.textContent = connected ? '1 台' : '0 台';
    }
    if (robotStatusEl) {
      const connected = robot.connected || false;
      const source = robot.source || 'NO_DATA';
      if (source === 'REAL' && connected) {
        robotStatusEl.textContent = '正常运行';
        robotStatusEl.style.color = 'var(--color-success)';
      } else if (source === 'NO_DATA') {
        robotStatusEl.textContent = '等待连接';
        robotStatusEl.style.color = 'var(--color-text-muted)';
      } else if (source === 'STALE') {
        robotStatusEl.textContent = '数据过时';
        robotStatusEl.style.color = 'var(--color-warning)';
      } else {
        robotStatusEl.textContent = '通信异常';
        robotStatusEl.style.color = 'var(--color-error)';
      }
    }

    // 机器狗运动状态
    const motionStateEl = document.getElementById('motion-state');
    if (motionStateEl) {
      const motionMap = {0:'静止',1:'站立',2:'行走',3:'慢跑',4:'上下楼',5:'摔倒'};
      motionStateEl.textContent = motionMap[robot.motion_state] || '—';
    }

    // 电量 - 双电池显示
    const batteryEl = document.getElementById('battery-pct');
    const batteryBar = document.getElementById('battery-bar');
    const batteryLeftEl = document.getElementById('battery-pct-left');
    const batteryRightEl = document.getElementById('battery-pct-right');
    const batteryBarLeft = document.getElementById('battery-bar-left');
    const batteryBarRight = document.getElementById('battery-bar-right');

    if (batteryEl) {
      const batt = robot.battery;
      batteryEl.textContent = batt == null ? '暂无数据' : `${batt}%`;
      batteryEl.className = 'battery-total' + (batt < 20 ? ' low' : batt < 40 ? ' medium' : '');
    }
    if (batteryBar && robot.battery != null) {
      batteryBar.style.width = `${robot.battery}%`;
      batteryBar.className = 'battery-bar-fill' + (robot.battery < 20 ? ' low' : robot.battery < 40 ? ' medium' : '');
    }

    // 前电池（左）
    if (batteryLeftEl) {
      const leftBatt = robot.battery_left;
      batteryLeftEl.textContent = leftBatt == null ? '-' : `${leftBatt}%`;
      batteryLeftEl.className = 'battery-value' + (leftBatt < 20 ? ' low' : leftBatt < 40 ? ' medium' : '');
    }
    if (batteryBarLeft && robot.battery_left != null) {
      batteryBarLeft.style.width = `${robot.battery_left}%`;
      batteryBarLeft.className = 'battery-bar-fill' + (robot.battery_left < 20 ? ' low' : robot.battery_left < 40 ? ' medium' : '');
    }

    // 后电池（右）
    if (batteryRightEl) {
      const rightBatt = robot.battery_right;
      batteryRightEl.textContent = rightBatt == null ? '-' : `${rightBatt}%`;
      batteryRightEl.className = 'battery-value' + (rightBatt < 20 ? ' low' : rightBatt < 40 ? ' medium' : '');
    }
    if (batteryBarRight && robot.battery_right != null) {
      batteryBarRight.style.width = `${robot.battery_right}%`;
      batteryBarRight.className = 'battery-bar-fill' + (robot.battery_right < 20 ? ' low' : robot.battery_right < 40 ? ' medium' : '');
    }
    
    // 圈数
    const lapsEl = document.getElementById('laps-count');
    if (lapsEl) {
      const loops = robot.nav_status?.loop_count || 0;
      lapsEl.textContent = loops;
    }
    
    // 覆盖率
    const coverageEl = document.getElementById('coverage-rate');
    if (coverageEl) {
      const rate = robot.coverage_rate || 0;
      coverageEl.textContent = `${rate}%`;
    }
    
    // 工单数
    const workOrdersEl = document.getElementById('work-orders');
    if (workOrdersEl) {
      const orders = window._state.get('workOrders') || [];
      const pending = orders.filter(o => o.status === 'pending').length;
      workOrdersEl.textContent = pending;
    }
  }

  _updateRobotPanel(robot, nav) {
    // 机器人状态
    const stateEl = document.getElementById('robot-state');
    if (stateEl) {
      const statusMap = {
        0: '待命', 1: '站立', 2: '行走', 3: '慢跑', 
        4: '上下楼', 5: '摔倒', 6: '软急停', 7: '充电中'
      };
      stateEl.textContent = `状态: ${statusMap[robot.motion_state] || '未知'}`;
    }
    
    // 位置
    const posEl = document.getElementById('robot-pos');
    if (posEl && robot.position) {
      posEl.textContent = `位置: (${robot.position.pos_x?.toFixed(2) || '—'}, ${robot.position.pos_y?.toFixed(2) || '—'})`;
    }
    
    // 速度
    const speedEl = document.getElementById('speed-state');
    if (speedEl) {
      const speed = robot.motion?.linear_x ?? 0;
      speedEl.textContent = speed > 0.01 ? `${speed.toFixed(2)} m/s` : '—';
    }
    
    // 导航状态
    const navEl = document.getElementById('nav-state');
    if (navEl) {
      const navStatusMap = {0: '待命中', 1: '定位中', 2: '导航中', 3: '到达目标', 4: '暂停', 5: '异常'};
      navEl.textContent = robot.nav_status != null ? (navStatusMap[robot.nav_status] || '未知') : '未连接';
    }

    // 步态
    const gaitEl = document.getElementById('gait-state');
    if (gaitEl) {
      const gaitMap = {'flat': '平地', 'stairs': '楼梯', 'agile': '敏捷', 'steady': '平稳'};
      gaitEl.textContent = robot.gait ? (gaitMap[robot.gait] || robot.gait) : '—';
    }
    
    // 姿态
    const poseEl = document.getElementById('pose-state');
    if (poseEl && robot.motion) {
      poseEl.textContent = `R:${(robot.motion.roll||0).toFixed(1)} P:${(robot.motion.pitch||0).toFixed(1)} Y:${(robot.motion.yaw||0).toFixed(1)}`;
    }
    
    // 最后更新
    const lastEl = document.getElementById('last-update');
    if (lastEl && robot.last_update) {
      const d = new Date(robot.last_update);
      lastEl.textContent = d.toLocaleTimeString('zh-CN');
    }
  }

  _updateEmergencyBtn(nav) {
    const authorizeBtn = document.getElementById('nav-authorize-btn');
    const deauthorizeBtn = document.getElementById('nav-deauthorize-btn');
    const panelStatus = document.getElementById('panel-status');
    
    // 更新控制面板状态指示器
    const isAuthorized = nav?.authorized && nav?.control_enabled;
    if (panelStatus) {
      panelStatus.className = 'panel-status' + (isAuthorized ? ' authorized' : '');
    }
    
    if (authorizeBtn) {
      authorizeBtn.disabled = isAuthorized;
    }
    
    if (deauthorizeBtn) {
      deauthorizeBtn.disabled = !isAuthorized;
    }
    
    // 更新所有控制按钮状态
    const controlBtnIds = [
      'motion-stand-btn',
      'motion-forward-btn',
      'motion-backward-btn',
      'motion-left-btn',
      'motion-right-btn',
      'motion-charge-btn',
      'motion-estop-btn'
    ];
    
    controlBtnIds.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.disabled = !isAuthorized;
    });
  }

  _updateAlertCount(robot) {
    const alertEl = document.getElementById('alert-count');
    if (alertEl) {
      const count = robot.errors?.length || 0;
      alertEl.textContent = `告警: ${count}`;
      alertEl.className = 'status-badge' + (count > 0 ? ' blocked' : ' ok');
    }
  }

  // ========== 视频墙 ==========
  
  _updateVideoWall() {
    const video = window._state.get('video') || {};
    const sources = video.sources || {};
    
    ['front', 'rear', 'thermal', 'body_front'].forEach(source => {
      const cameraEl = document.querySelector(`.camera[data-source="${source}"]`);
      if (!cameraEl) return;
      
      const stateEl = cameraEl.querySelector('.camera-status');
      const videoEl = cameraEl.querySelector('.camera-video');
      const placeholderEl = cameraEl.querySelector('.camera-placeholder');
      
      const config = sources[source];
      if (!config) {
        if (stateEl) {
          stateEl.className = 'camera-status offline';
          stateEl.textContent = '● 未配置';
        }
        return;
      }
      
      const state = config.state || 'unverified';
      
      if (state === 'online') {
        if (stateEl) {
          stateEl.className = 'camera-status online';
          stateEl.textContent = '● 在线';
        }
        cameraEl.classList.add('connected');
        cameraEl.classList.remove('unverified', 'connecting');
        
        if (videoEl && config.playback_url) {
          videoEl.src = config.playback_url;
          videoEl.style.display = 'block';
          videoEl.classList.add('active');
        }
        if (placeholderEl) {
          placeholderEl.classList.add('hidden');
          placeholderEl.style.display = 'none';
        }
      } else if (state === 'blocked') {
        if (stateEl) {
          stateEl.className = 'camera-status offline';
          stateEl.textContent = '● 受限';
        }
        cameraEl.classList.remove('connected', 'connecting');
        cameraEl.classList.add('unverified');
        if (videoEl) {
          videoEl.style.display = 'none';
          videoEl.classList.remove('active');
        }
        if (placeholderEl) {
          placeholderEl.classList.remove('hidden');
          placeholderEl.style.display = 'flex';
        }
      } else {
        // connecting or unverified
        if (state === 'connecting') {
          if (stateEl) {
            stateEl.className = 'camera-status unverified';
            stateEl.textContent = '● 连接中...';
          }
          cameraEl.classList.add('connecting');
        } else {
          if (stateEl) {
            stateEl.className = 'camera-status unverified';
            stateEl.textContent = '● 未验证';
          }
          cameraEl.classList.remove('connecting');
        }
        cameraEl.classList.remove('connected');
        cameraEl.classList.add('unverified');
        if (videoEl) {
          videoEl.style.display = 'none';
          videoEl.classList.remove('active');
        }
        if (placeholderEl) {
          placeholderEl.classList.remove('hidden');
          placeholderEl.style.display = 'flex';
        }
      }
    });
  }

  // ========== 时间线 ==========
  
  _updateTimeline(robot) {
    const lapsContainer = document.getElementById('timeline-laps');
    if (!lapsContainer) return;
    
    const loopCount = robot.nav_status?.loop_count || 0;
    const totalLaps = Math.max(5, loopCount + 2);
    
    let html = '';
    for (let i = 1; i <= totalLaps; i++) {
      let cls = 'pending';
      if (i < loopCount) cls = 'completed';
      else if (i === loopCount) cls = 'in-progress';
      html += `<div class="lap ${cls}">${i}</div>`;
    }
    lapsContainer.innerHTML = html;
    
    // 距离统计
    const inspectedEl = document.getElementById('inspected-dist');
    const totalEl = document.getElementById('total-dist');
    if (inspectedEl && robot.position?.distance) {
      inspectedEl.textContent = robot.position.distance.toFixed(1);
    }
    if (totalEl) {
      totalEl.textContent = (robot.position?.distance || 0).toFixed(1);
    }
    
    // 异常数
    const errorsEl = document.getElementById('timeline-errors');
    if (errorsEl && robot.errors) {
      errorsEl.textContent = robot.errors.length;
    }
  }

  // ========== 地图 ==========
  
  _initMap() {
    const canvas = document.getElementById('map-canvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    const resize = () => {
      const rect = canvas.parentElement.getBoundingClientRect();
      canvas.width = rect.width;
      canvas.height = rect.height;
    };
    resize();
    window.addEventListener('resize', resize);
    
    // 模拟巡检点
    this._mapPoints = [
      { x: 0.2, y: 0.3, label: '展厅入口', type: 'point' },
      { x: 0.5, y: 0.2, label: '展车区', type: 'point' },
      { x: 0.8, y: 0.4, label: '售后车间', type: 'point' },
      { x: 0.3, y: 0.7, label: '停车场', type: 'point' },
      { x: 0.6, y: 0.8, label: '充电桩', type: 'point' },
    ];
    
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // 网格背景
      ctx.strokeStyle = 'rgba(100, 140, 200, 0.1)';
      ctx.lineWidth = 1;
      for (let i = 0; i < canvas.width; i += 40) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i, canvas.height);
        ctx.stroke();
      }
      for (let i = 0; i < canvas.height; i += 40) {
        ctx.beginPath();
        ctx.moveTo(0, i);
        ctx.lineTo(canvas.width, i);
        ctx.stroke();
      }
      
      // 巡检点
      this._mapPoints.forEach(p => {
        const x = p.x * canvas.width;
        const y = p.y * canvas.height;
        
        ctx.beginPath();
        ctx.arc(x, y, 8, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(251, 191, 36, 0.6)';
        ctx.fill();
        ctx.strokeStyle = '#FBBF24';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        ctx.fillStyle = '#A8B8D0';
        ctx.font = '11px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(p.label, x, y - 14);
      });
      
      // 机器人位置
      const robot = window._state.get('robot') || {};
      if (robot.position?.pos_x != null) {
        const rx = ((robot.position.pos_x + 10) / 20) * canvas.width;
        const ry = ((robot.position.pos_y + 10) / 20) * canvas.height;
        
        ctx.beginPath();
        ctx.arc(rx, ry, 12, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(0, 160, 233, 0.8)';
        ctx.fill();
        ctx.strokeStyle = '#00A0E9';
        ctx.lineWidth = 3;
        ctx.stroke();
        
        // 脉冲效果
        const time = Date.now() / 1000;
        const pulse = (Math.sin(time * 3) + 1) / 2;
        ctx.beginPath();
        ctx.arc(rx, ry, 12 + pulse * 10, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(0, 160, 233, ${0.3 - pulse * 0.2})`;
        ctx.lineWidth = 2;
        ctx.stroke();
      }
      
      this._mapAnimFrame = requestAnimationFrame(draw);
    };
    
    draw();
  }

  _updateMap(robot) {
    // 地图由animation frame自动更新
  }

  // ========== 云台控制 ==========
  
  _updateGimbalPanel(data) {
    if (!data || !data.state) return;
    
    const yaw = document.getElementById('gimbal-yaw');
    const pitch = document.getElementById('gimbal-pitch');
    const roll = document.getElementById('gimbal-roll');
    const zoom = document.getElementById('gimbal-zoom');
    
    if (yaw && data.state.yaw != null) yaw.textContent = `${data.state.yaw.toFixed(1)}°`;
    if (pitch && data.state.pitch != null) pitch.textContent = `${data.state.pitch.toFixed(1)}°`;
    if (roll && data.state.roll != null) roll.textContent = `${data.state.roll.toFixed(1)}°`;
    if (zoom) zoom.textContent = `${data.state.zoom || 1}x`;
  }

  // ========== 事件监听 ==========
  
  _initEventListeners() {
    // 视频控制
    document.querySelectorAll('[data-camera-action]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const action = e.target.dataset.cameraAction;
        const camera = e.target.dataset.camera;
        this._handleCameraAction(action, camera);
      });
    });
    
    // 导航授权
    document.getElementById('nav-authorize-btn')?.addEventListener('click', async () => {
      try {
        await window._api.authorizeMotion();
        await this._fetchNavStatus();
        if (Toast) Toast.success('控制授权成功');
      } catch (e) {
        this._showControlError(`授权失败: ${e.message}`);
      }
    });
    
    document.getElementById('nav-deauthorize-btn')?.addEventListener('click', async () => {
      try {
        await window._api.deauthorizeMotion();
        await this._fetchNavStatus();
        if (Toast) Toast.info('控制已撤销');
      } catch (e) {
        this._showControlError(`撤销失败: ${e.message}`);
      }
    });
    
    // 模式切换
    document.querySelectorAll('.mode-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const mode = btn.dataset.mode;
        try {
          // 映射UI模式到协议模式: normal=0, assist=1, navigation=2
          const modeMap = { 'normal': 0, 'assist': 1, 'navigation': 2 };
          await window._api.switchMode(modeMap[mode]);
          this._showControlMessage(`已切换到${btn.title}`);
        } catch (e) {
          this._showControlError(`模式切换失败: ${e.message}`);
        }
      });
    });
    
    // 方向控制（游戏手柄）
    const axisMap = {
      'motion-forward-btn': { x: 0, y: 1 },
      'motion-backward-btn': { x: 0, y: -1 },
      'motion-left-btn': { x: -1, y: 0 },
      'motion-right-btn': { x: 1, y: 0 }
    };
    
    Object.entries(axisMap).forEach(([id, {x, y}]) => {
      document.getElementById(id)?.addEventListener('click', async () => {
        try {
          await window._api.motionAxis(x, y, 0);
        } catch (e) {
          this._showControlError(`移动失败: ${e.message}`);
        }
      });
    });
    
    // 站立
    document.getElementById('motion-stand-btn')?.addEventListener('click', async () => {
      try {
        await window._api.motionState(1); // MOTION_STATE_STAND
        this._showControlMessage('机器狗已站立');
      } catch (e) {
        this._showControlError(`站立失败: ${e.message}`);
      }
    });
    
    // 回充
    document.getElementById('motion-charge-btn')?.addEventListener('click', async () => {
      try {
        await window._api.chargeControl(1); // CHARGE_START
        this._showControlMessage('已发送回充指令');
      } catch (e) {
        this._showControlError(`回充失败: ${e.message}`);
      }
    });
    
    // 紧急停止
    document.getElementById('motion-estop-btn')?.addEventListener('click', async () => {
      const confirmed = await Toast.confirm('确认执行紧急停止？此操作将立即停止机器狗所有运动。');
      if (!confirmed) return;
      window.handleEmergencyStop();
    });
    
    // 云台连接
    document.getElementById('gimbal-connect-btn')?.addEventListener('click', () => {
      document.getElementById('gimbal-modal').classList.add('active');
    });
    
    document.getElementById('gimbal-modal-cancel')?.addEventListener('click', () => {
      document.getElementById('gimbal-modal').classList.remove('active');
    });
    
    document.getElementById('gimbal-modal-connect')?.addEventListener('click', async () => {
      const host = document.getElementById('gimbal-host').value.trim();
      const username = document.getElementById('gimbal-username').value.trim();
      const password = document.getElementById('gimbal-password').value;
      const errEl = document.getElementById('gimbal-modal-error');
      
      errEl.textContent = '';
      
      try {
        await window._api.connectGimbal(host, username, password);
        document.getElementById('gimbal-modal').classList.remove('active');
        await this._fetchGimbalState();
      } catch (e) {
        errEl.textContent = e.message;
      }
    });
    
    // 云台扫描
    document.getElementById('gimbal-scan-btn')?.addEventListener('click', async () => {
      try {
        const result = await window._api.scanGimbal();
        Toast.success(`扫描完成，找到 ${result.hosts?.length || 0} 个设备`);
      } catch (e) {
        Toast.error(`扫描失败: ${e.message}`);
      }
    });
  }

  _handleCameraAction(action, camera) {
    switch (action) {
      case 'start':
        this._startVideo(camera);
        break;
      case 'probe':
        this._probeVideo(camera);
        break;
      case 'fullscreen':
        this._toggleFullscreen(camera);
        break;
      case 'capture':
        this._captureFrame(camera);
        break;
    }
  }

  _startVideo(source) {
    window._api.startVideo(source).then(() => {
      this._fetchVideo();
    }).catch(e => {
      Toast.error(`启动视频失败: ${e.message}`);
    });
  }

  _probeVideo(source) {
    window._api.probeVideoStream(source).then(() => {
      this._fetchVideo();
    }).catch(e => {
      Toast.error(`探测视频失败: ${e.message}`);
    });
  }

  _toggleFullscreen(cameraId) {
    const video = document.getElementById('video-' + cameraId);
    if (!video) return;
    
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      video.requestFullscreen().catch(e => console.error('Fullscreen error:', e));
    }
  }

  _captureFrame(cameraId) {
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
  }

  _showControlError(message) {
    const el = document.getElementById('control-message');
    if (el) {
      el.textContent = message;
      el.style.color = 'var(--color-error)';
      setTimeout(() => { el.textContent = ''; }, 5000);
    }
  }
  
  _showControlMessage(message) {
    const el = document.getElementById('control-message');
    if (el) {
      el.textContent = message;
      el.style.color = 'var(--color-success)';
      setTimeout(() => { el.textContent = ''; }, 3000);
    }
  }

  // ========== 视频自动启动 ==========

  _autoStartVideo() {
    const video = window._state.get('video') || {};
    const sources = video.sources || {};
    
    // 只启动front和rear摄像头（thermal和body_front需要额外探测）
    ['front', 'rear'].forEach(source => {
      const config = sources[source];
      // 条件：有RTSP地址 且 状态不是online且不是connecting
      if (config && config.rtsp_url && config.state !== 'online' && config.state !== 'connecting') {
        console.log(`[Dashboard] Auto-starting video for ${source}: ${config.rtsp_url}`);
        this._startVideo(source);
      }
    });
  }
}

if (typeof module !== 'undefined' && module.exports) module.exports = { DashboardView };