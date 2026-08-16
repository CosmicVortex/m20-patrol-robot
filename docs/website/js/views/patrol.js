/**
 * PatrolView - 巡逻管理视图
 * 
 * 功能：
 * - 巡逻任务列表（Tab切换）
 * - 异常工单管理
 * - 巡检点配置
 * - 任务创建与编辑
 */
class PatrolView {
  constructor() {
    this._content = null;
    this._currentTab = 'tasks';
  }
  
  async init() {
    this._content = document.querySelector('#view-patrol #patrol-content');
    if (!this._content) return;

    // 加载初始数据
    await window._api.fetchWorkOrders();
    await window._api.fetchInspectionPoints();

    this._renderTabs();
    await this._loadTabData(this._currentTab);
  }

  destroy() {
    this._content = null;
  }

  render() {
    this._loadTabData(this._currentTab);
  }

  _renderTabs() {
    const tabsContainer = document.getElementById('patrol-tabs');
    if (!tabsContainer) return;
    
    tabsContainer.innerHTML = `
      <button class="tab ${this._currentTab === 'tasks' ? 'active' : ''}" data-tab="tasks">巡逻任务</button>
      <button class="tab ${this._currentTab === 'orders' ? 'active' : ''}" data-tab="orders">异常工单</button>
      <button class="tab ${this._currentTab === 'points' ? 'active' : ''}" data-tab="points">巡检点</button>
    `;
    
    tabsContainer.querySelectorAll('.tab').forEach(btn => {
      btn.addEventListener('click', () => {
        this._currentTab = btn.dataset.tab;
        this._renderTabs();
        this._loadTabData(this._currentTab);
      });
    });
  }

  async _loadTabData(tab) {
    this._content.innerHTML = '<div class="loading"><div class="loading-spinner"></div></div>';
    
    try {
      switch (tab) {
        case 'tasks':
          await this._loadTasks();
          break;
        case 'orders':
          await this._loadOrders();
          break;
        case 'points':
          await this._loadPoints();
          break;
      }
    } catch (error) {
      this._content.innerHTML = `<div class="empty-state"><h3>数据加载失败</h3><p>${this._escapeHtml(error.message)}</p><button class="btn btn-primary" onclick="window._router.refresh()">重试</button></div>`;
    }
  }

  async _loadTasks() {
    const tasks = window._state.get('tasks') || [];
    const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    
    let html = `
      <div class="card">
        <h3>新建巡逻任务</h3>
        <form id="new-task-form">
          <div class="form-row">
            <div class="form-group">
              <label>任务名称</label>
              <input type="text" name="name" class="input" placeholder="例如：展厅日常巡逻" required>
            </div>
            <div class="form-group">
              <label>任务类型</label>
              <select name="type" class="input">
                <option value="daily">日常巡</option>
                <option value="special">专项巡</option>
                <option value="closing">闭店巡</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>检查项模板</label>
              <select name="template" class="input">
                <option value="showroom">展厅检查</option>
                <option value="service">售后检查</option>
                <option value="parking">停车场检查</option>
              </select>
            </div>
            <div class="form-group">
              <label>计划执行时间</label>
              <input type="datetime-local" name="scheduled_time" class="input">
            </div>
          </div>
          <button type="submit" class="btn btn-primary">发送任务</button>
        </form>
      </div>
      <div class="card mt-4">
        <h3>任务列表</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>任务ID</th>
                <th>名称</th>
                <th>类型</th>
                <th>状态</th>
                <th>执行时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
    `;
    
    if (tasks.length === 0) {
      html += '<tr><td colspan="6" class="empty-state">暂无任务</td></tr>';
    } else {
      tasks.forEach(task => {
        html += `
          <tr>
            <td>${esc(task.id)}</td>
            <td>${esc(task.name)}</td>
            <td>${esc(task.type || '日常巡')}</td>
            <td><span class="status-badge ${task.status === 'executing' ? 'ok' : task.status === 'pending' ? 'warn' : ''}">${esc(task.status || 'pending')}</span></td>
            <td>${esc(task.scheduled_time || '—')}</td>
            <td>
              <button class="btn" data-cancel-task="${esc(task.id)}">取消</button>
            </td>
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
    
    // 绑定事件
    document.getElementById('new-task-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = new FormData(e.target);
      try {
        await window._api.createTask({
          name: form.get('name'),
          type: form.get('type'),
          template: form.get('template'),
          scheduled_time: form.get('scheduled_time')
        });
        await this._loadTasks();
      } catch (err) {
        Toast.error(`创建任务失败: ${err.message}`);
      }
    });

    document.querySelectorAll('[data-cancel-task]').forEach(btn => {
      btn.addEventListener('click', async () => {
        try {
          await window._api.cancelTask(btn.dataset.cancelTask);
          await this._loadTasks();
        } catch (err) {
          Toast.error(`取消任务失败: ${err.message}`);
        }
      });
    });
  }

  async _loadOrders() {
    const orders = window._state.get('workOrders') || [];
    const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    
    let html = `
      <div class="card">
        <h3>新建工单</h3>
        <form id="new-order-form">
          <div class="form-row">
            <div class="form-group">
              <label>工单标题</label>
              <input type="text" name="title" class="input" placeholder="例如：展厅A区展车异常" required>
            </div>
            <div class="form-group">
              <label>位置</label>
              <input type="text" name="location" class="input" placeholder="例如：展厅-A区-03">
            </div>
          </div>
          <div class="form-group">
            <label>描述</label>
            <textarea name="description" class="input" rows="3" placeholder="详细描述异常情况..."></textarea>
          </div>
          <button type="submit" class="btn btn-primary">创建工单</button>
        </form>
      </div>
      <div class="card mt-4">
        <h3>工单列表</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>编号</th>
                <th>标题</th>
                <th>位置</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
    `;
    
    if (orders.length === 0) {
      html += '<tr><td colspan="6" class="empty-state">暂无工单</td></tr>';
    } else {
      orders.forEach(order => {
        html += `
          <tr>
            <td>${esc(order.id)}</td>
            <td>${esc(order.title)}</td>
            <td>${esc(order.location || '未配置')}</td>
            <td>
              <select class="input form-select-sm" data-order-status="${esc(order.id)}" style="width:auto;padding:var(--space-1) var(--space-2)">
                <option value="pending" ${order.status==='pending'?'selected':''}>待处理</option>
                <option value="in_progress" ${order.status==='in_progress'?'selected':''}>处理中</option>
                <option value="completed" ${order.status==='completed'?'selected':''}>已完成</option>
              </select>
            </td>
            <td>${esc(order.created_at || '—')}</td>
            <td>
              <button class="btn" data-update-order="${esc(order.id)}">保存</button>
            </td>
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
    
    // 绑定事件
    document.getElementById('new-order-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = new FormData(e.target);
      try {
        await window._api.createWorkOrder({
          title: form.get('title'),
          location: form.get('location'),
          description: form.get('description')
        });
        await this._loadOrders();
      } catch (err) {
        Toast.error(`创建工单失败: ${err.message}`);
      }
    });

    document.querySelectorAll('[data-update-order]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.updateOrder;
        const status = document.querySelector(`[data-order-status="${CSS.escape(id)}"]`).value;
        try {
          await window._api.updateWorkOrder(id, { status });
          await this._loadOrders();
        } catch (err) {
          Toast.error(`更新工单失败: ${err.message}`);
        }
      });
    });
  }

  async _loadPoints() {
    const points = window._state.get('inspectionPoints') || [];
    const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    
    let html = `
      <div class="card">
        <h3>添加巡检点</h3>
        <form id="new-point-form">
          <div class="form-row">
            <div class="form-group">
              <label>巡检点名称</label>
              <input type="text" name="name" class="input" placeholder="例如：展厅入口" required>
            </div>
            <div class="form-group">
              <label>区域</label>
              <input type="text" name="area" class="input" placeholder="例如：展厅">
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>地图坐标X</label>
              <input type="number" name="x" class="input" step="0.1" placeholder="0.0 - 20.0">
            </div>
            <div class="form-group">
              <label>地图坐标Y</label>
              <input type="number" name="y" class="input" step="0.1" placeholder="0.0 - 15.0">
            </div>
          </div>
          <button type="submit" class="btn btn-primary">添加巡检点</button>
        </form>
      </div>
      <div class="card mt-4">
        <h3>巡检点列表</h3>
        <ul class="list-reset">
    `;
    
    if (points.length === 0) {
      html += '<li class="empty-state p-4">暂无巡检点配置</li>';
    } else {
      points.forEach(point => {
        html += `
          <li class="timeline-item">
            <div>
              <strong>${esc(point.name || point.id)}</strong>
              <span class="ml-2-muted">${esc(point.area || '未配置区域')}</span>
            </div>
            <button class="btn btn-danger" data-delete-point="${esc(point.id)}">删除</button>
          </li>
        `;
      });
    }
    
    html += `
        </ul>
      </div>
    `;
    
    this._content.innerHTML = html;
    
    // 绑定事件
    document.getElementById('new-point-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = new FormData(e.target);
      try {
        await window._api.createInspectionPoint({
          name: form.get('name'),
          area: form.get('area'),
          x: parseFloat(form.get('x')) || 0,
          y: parseFloat(form.get('y')) || 0
        });
        await this._loadPoints();
      } catch (err) {
        Toast.error(`添加巡检点失败: ${err.message}`);
      }
    });

    document.querySelectorAll('[data-delete-point]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const confirmed = await Toast.confirm('确认删除该巡检点？');
        if (!confirmed) return;
        try {
          await window._api.deleteInspectionPoint(btn.dataset.deletePoint);
          await this._loadPoints();
        } catch (err) {
          Toast.error(`删除巡检点失败: ${err.message}`);
        }
      });
    });
  }

  _escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
}

if (typeof module !== 'undefined' && module.exports) module.exports = { PatrolView };