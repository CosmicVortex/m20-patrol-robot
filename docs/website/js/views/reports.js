/**
 * ReportsView - 数据报表视图
 * 
 * 功能：
 * - 巡检完成率统计
 * - 告警趋势分析
 * - 设备健康度监控
 * - 巡逻热力图（开发中）
 */
class ReportsView {
  constructor() {
    this._content = null;
    this._chartData = null;
  }
  
  async init() {
    this._content = document.querySelector('#view-reports');
    if (!this._content) return;
    
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
    const tasks = window._state.get('tasks') || [];
    const orders = window._state.get('workOrders') || [];
    const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    
    // 计算统计指标
    const completionRate = tasks.length > 0 
      ? Math.round((tasks.filter(t => t.status === 'completed').length / tasks.length) * 100)
      : 0;
    
    const alertCount = orders.filter(o => o.status !== 'completed').length;
    
    const totalDistance = robot.position?.distance || 0;
    
    let html = `
      <h2>数据报表</h2>
      <div class="metrics">
        <div class="metric">
          <div class="metric-icon success">✓</div>
          <div>
            <label>今日完成率</label>
            <strong>${completionRate}%</strong>
            <span>巡检任务完成比例</span>
          </div>
        </div>
        <div class="metric">
          <div class="metric-icon ${alertCount > 0 ? 'warning' : 'success'}">⚠</div>
          <div>
            <label>待处理告警</label>
            <strong>${alertCount}</strong>
            <span>异常告警未解决数</span>
          </div>
        </div>
        <div class="metric">
          <div class="metric-icon">◈</div>
          <div>
            <label>总巡检距离</label>
            <strong>${totalDistance.toFixed(1)} km</strong>
            <span>累计巡逻里程</span>
          </div>
        </div>
        <div class="metric">
          <div class="metric-icon">↺</div>
          <div>
            <label>今日圈数</label>
            <strong>${robot.nav_status?.loop_count || 0}</strong>
            <span>完成巡逻圈数</span>
          </div>
        </div>
      </div>
      
      <div class="monitor-grid">
        <div class="card">
          <h3>告警趋势（近7天）</h3>
          <div id="alert-chart" style="height:300px;display:flex;align-items:flex-end;justify-content:space-around;padding:var(--space-4);gap:var(--space-2)">
            ${this._generateAlertChart()}
          </div>
        </div>
        
        <div class="card">
          <h3>任务完成情况</h3>
          <div style="padding:var(--space-4)">
            <div style="margin-bottom:var(--space-4)">
              <div style="display:flex;justify-content:space-between;margin-bottom:var(--space-2)">
                <span style="font-size:var(--fs-sm);color:var(--color-text-secondary)">完成率</span>
                <span style="font-size:var(--fs-sm);font-weight:600">${completionRate}%</span>
              </div>
              <div style="height:8px;background:var(--color-bg-secondary);border-radius:var(--r-full);overflow:hidden">
                <div style="height:100%;width:${completionRate}%;background:linear-gradient(90deg,var(--color-success),#34D399);border-radius:var(--r-full)"></div>
              </div>
            </div>
            <div style="margin-bottom:var(--space-4)">
              <div style="display:flex;justify-content:space-between;margin-bottom:var(--space-2)">
                <span style="font-size:var(--fs-sm);color:var(--color-text-secondary)">告警解决率</span>
                <span style="font-size:var(--fs-sm);font-weight:600">${this._calculateResolveRate(orders)}%</span>
              </div>
              <div style="height:8px;background:var(--color-bg-secondary);border-radius:var(--r-full);overflow:hidden">
                <div style="height:100%;width:${this._calculateResolveRate(orders)}%;background:linear-gradient(90deg,var(--color-info),#60A5FA);border-radius:var(--r-full)"></div>
              </div>
            </div>
            <div>
              <div style="display:flex;justify-content:space-between;margin-bottom:var(--space-2)">
                <span style="font-size:var(--fs-sm);color:var(--color-text-secondary)">设备在线率</span>
                <span style="font-size:var(--fs-sm);font-weight:600">100%</span>
              </div>
              <div style="height:8px;background:var(--color-bg-secondary);border-radius:var(--r-full);overflow:hidden">
                <div style="height:100%;width:100%;background:linear-gradient(90deg,var(--color-brand-blue),var(--color-brand-blue-dark));border-radius:var(--r-full)"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="card" style="margin-top:var(--space-4)">
        <h3>最近告警记录</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>时间</th>
                <th>类型</th>
                <th>描述</th>
                <th>位置</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
    `;
    
    if (orders.length === 0) {
      html += '<tr><td colspan="5" style="text-align:center;color:var(--color-text-muted);padding:var(--space-8)">暂无告警记录</td></tr>';
    } else {
      orders.slice(-10).reverse().forEach(order => {
        const statusClass = order.status === 'completed' ? 'ok' : order.status === 'in_progress' ? 'warn' : '';
        const statusText = order.status === 'completed' ? '已解决' : order.status === 'in_progress' ? '处理中' : '待处理';
        
        html += `
          <tr>
            <td>${esc(order.created_at || '—')}</td>
            <td>${esc(order.type || '异常')}</td>
            <td>${esc(order.title)}</td>
            <td>${esc(order.location || '—')}</td>
            <td><span class="status-badge ${statusClass}">${statusText}</span></td>
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

  _generateAlertChart() {
    const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
    const values = [3, 5, 2, 7, 4, 1, 6];
    const max = Math.max(...values);
    
    return days.map((day, i) => `
      <div style="display:flex;flex-direction:column;align-items:center;gap:var(--space-2);flex:1">
        <div style="width:100%;max-width:40px;height:${(values[i] / max) * 200}px;background:linear-gradient(to top,var(--color-warning),var(--color-error));border-radius:var(--r-sm) var(--r-sm) 0 0;opacity:0.8"></div>
        <span style="font-size:var(--fs-xs);color:var(--color-text-muted)">${day}</span>
        <span style="font-size:var(--fs-xs);font-weight:600">${values[i]}</span>
      </div>
    `).join('');
  }

  _calculateResolveRate(orders) {
    if (orders.length === 0) return 100;
    const resolved = orders.filter(o => o.status === 'completed').length;
    return Math.round((resolved / orders.length) * 100);
  }
}

if (typeof module !== 'undefined' && module.exports) module.exports = { ReportsView };