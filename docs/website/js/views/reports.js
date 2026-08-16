/**
 * ReportsView - 数据报表视图
 * 
 * 功能：
 * - 巡检完成率统计
 * - 告警趋势分析
 * - 设备健康度监控
 */
class ReportsView {
  constructor() {
    this._content = null;
    this._chartData = null;
  }
  
  async init() {
    this._content = document.querySelector('#view-reports');
    if (!this._content) return;

    // 加载初始数据
    await Promise.all([
      window._api.fetchWorkOrders(),
      window._api.fetchStatus()
    ]);

    await this._loadReports();
  }
  
  destroy() {
    this._content = null;
  }
  
  render() {
    this._loadReports();
  }

  async _loadReports() {
    const robot = window._state.get('robot') || {};
    const orders = window._state.get('workOrders') || [];
    const navStatus = window._state.get('navigation') || {};
    const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    
    // 计算统计指标
    const pendingOrders = orders.filter(o => o.status !== 'completed').length;
    const loopCount = navStatus.loop_count || 0;
    const resolveRate = orders.length > 0
      ? Math.round((orders.filter(o => o.status === 'completed').length / orders.length) * 100)
      : 0;

    // 累计巡逻里程（从robot.total_distance获取，单位km）
    const totalDistance = robot.total_distance || 0;
    const distanceKm = totalDistance > 0 ? (totalDistance / 1000).toFixed(2) : '—';

    // 设备在线率 - 根据机器人连接状态显示
    const connected = robot.connected || false;
    const source = robot.source || 'NO_DATA';
    const deviceOnlineRate = (source === 'REAL' && connected) ? 100 : 0;
    const deviceStatusText = source === 'REAL' && connected ? '在线' : '离线';

    // 告警趋势数据 - 基于工单数据计算，无数据时显示"暂无数据"
    const alertChartData = this._generateAlertChartData(orders);
    
    let html = `
      <h2>数据报表</h2>
      <div class="metrics">
        <div class="metric">
          <div class="metric-icon success">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
          </div>
          <div>
            <label>待处理告警</label>
            <strong>${pendingOrders}</strong>
            <span>异常告警未解决数</span>
          </div>
        </div>
        <div class="metric">
          <div class="metric-icon ${pendingOrders > 0 ? 'warning' : 'success'}">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          </div>
          <div>
            <label>告警解决率</label>
            <strong>${resolveRate}%</strong>
            <span>已完成/总数</span>
          </div>
        </div>
        <div class="metric">
          <div class="metric-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/></svg>
          </div>
          <div>
            <label>累计巡逻里程</label>
            <strong>${distanceKm} km</strong>
            <span>基于nav_status.total_distance</span>
          </div>
        </div>
        <div class="metric">
          <div class="metric-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
          </div>
          <div>
            <label>今日圈数</label>
            <strong>${loopCount}</strong>
            <span>完成巡逻圈数</span>
          </div>
        </div>
      </div>
      
      <div class="monitor-grid">
        <div class="card">
          <h3>告警趋势（近7天）</h3>
          <div id="alert-chart" class="chart-container">
            ${alertChartData}
          </div>
        </div>

        <div class="card">
          <h3>任务完成情况</h3>
          <div class="p-4">
            <div class="progress-row">
              <div class="progress-row-label">
                <span>告警解决率</span>
                <span>${resolveRate}%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-bar-fill success" style="width:${resolveRate}%"></div>
              </div>
            </div>
            <div class="progress-row">
              <div class="progress-row-label">
                <span>待处理工单</span>
                <span>${pendingOrders}</span>
              </div>
              <div class="progress-bar">
                <div class="progress-bar-fill warning" style="width:${Math.min(100, pendingOrders * 10)}%"></div>
              </div>
            </div>
            <div class="progress-row">
              <div class="progress-row-label">
                <span>设备在线率</span>
                <span>${deviceOnlineRate}% (${deviceStatusText})</span>
              </div>
              <div class="progress-bar">
                <div class="progress-bar-fill brand" style="width:${deviceOnlineRate}%"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="card mt-4">
        <h3>最近告警记录</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>编号</th>
                <th>标题</th>
                <th>位置</th>
                <th>状态</th>
                <th>创建时间</th>
              </tr>
            </thead>
            <tbody>
    `;
    
    if (orders.length === 0) {
      html += '<tr><td colspan="5" class="empty-center">暂无告警记录</td></tr>';
    } else {
      orders.slice(-10).reverse().forEach(order => {
        const statusClass = order.status === 'completed' ? 'ok' : order.status === 'in_progress' ? 'warn' : '';
        const statusText = order.status === 'completed' ? '已解决' : order.status === 'in_progress' ? '处理中' : '待处理';
        
        html += `
          <tr>
            <td>${esc(order.id || '—')}</td>
            <td>${esc(order.title || '—')}</td>
            <td>${esc(order.location || '—')}</td>
            <td><span class="status-badge ${statusClass}">${statusText}</span></td>
            <td>${esc(order.created_at?.slice(0, 16) || '—')}</td>
          </tr>
        `;
      });
    }
    
    html += `
            </tbody>
          </table>
        </div>
      </div>
    `;
    
    this._content.innerHTML = html;
  }

  _generateAlertChartData(orders) {
    if (orders.length === 0) {
      return '<div class="empty-center">暂无数据</div>';
    }

    // 基于工单创建时间统计最近7天数据
    const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    const now = new Date();
    const values = [];

    for (let i = 6; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      const dayOfWeek = date.getDay();
      const dayName = days[dayOfWeek === 0 ? 6 : dayOfWeek - 1];
      const dateStr = date.toISOString().split('T')[0];

      const count = orders.filter(o => o.created_at && o.created_at.startsWith(dateStr)).length;
      values.push({ day: dayName, count });
    }

    const maxVal = Math.max(...values.map(v => v.count), 1);

    return values.map(v => `
      <div class="chart-bar-wrapper">
        <div class="chart-bar warning" style="height:${(v.count / maxVal) * 200}px" title="${v.count} 条"></div>
        <span class="chart-bar-label">${v.day}</span>
      </div>
    `).join('');
  }

  _calculateResolveRate(orders) {
    if (orders.length === 0) return 0;
    return Math.round((orders.filter(o => o.status === 'completed').length / orders.length) * 100);
  }

  _escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
}

if (typeof module !== 'undefined' && module.exports) module.exports = { ReportsView };
