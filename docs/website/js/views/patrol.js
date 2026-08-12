/** Patrol management view backed by work-order, inspection-point and timeline APIs. */
class PatrolView {
  constructor() { this._content = null; }
  async init() {
    this._content = document.querySelector('.content');
    if (!this._content) return;
    this._content.innerHTML = '<section class="view-container"><h2>巡逻管理</h2><p>正在读取巡逻数据…</p></section>';
    try {
      const [orders, points, timeline, nav] = await Promise.all([
        window._api.fetchWorkOrders(), window._api.fetchInspectionPoints(),
        window._api.fetchTimeline(), window._api.fetchNavStatus(),
      ]);
      this._render({ orders: orders.orders || [], summary: orders.summary || {}, points: points.points || [], timeline: timeline.entries || [], nav });
    } catch (error) {
      const message = String(error.message || error).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
      this._content.innerHTML = `<section class="view-container"><h2>巡逻管理</h2><p>数据读取失败：${message}</p><button class="btn-primary" id="patrol-retry">重试</button></section>`;
      this._content.querySelector('#patrol-retry')?.addEventListener('click', () => this.init());
    }
  }
  destroy() { this._content = null; }
  _render(data) {
    if (!this._content) return;
    const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const orderRows = data.orders.length ? data.orders.map(order => `
      <tr><td>${esc(order.id)}</td><td>${esc(order.title)}</td><td>${esc(order.location || '未配置')}</td>
      <td><select data-order-status="${esc(order.id)}"><option value="pending" ${order.status==='pending'?'selected':''}>待处理</option><option value="in_progress" ${order.status==='in_progress'?'selected':''}>处理中</option><option value="completed" ${order.status==='completed'?'selected':''}>已完成</option></select></td>
      <td><button class="btn-secondary" data-update-order="${esc(order.id)}">保存</button></td></tr>`).join('') : '<tr><td colspan="5">暂无工单</td></tr>';
    const pointRows = data.points.length ? data.points.map(point => `<li><strong>${esc(point.name || point.id || '巡检点')}</strong> · ${esc(point.area || '未配置区域')}</li>`).join('') : '<li>暂无巡检点配置</li>';
    const timelineRows = data.timeline.length ? data.timeline.slice(-8).reverse().map(item => `<li><strong>${esc(item.type || '事件')}</strong> ${esc(item.message || item.description || '')}</li>`).join('') : '<li>暂无巡逻时间线</li>';
    this._content.innerHTML = `<section class="view-container"><h2>巡逻管理</h2>
      <div class="metrics"><div class="metric"><div><label>工单总数</label><strong>${data.summary.total ?? data.orders.length}</strong></div></div><div class="metric"><div><label>待处理</label><strong>${data.summary.pending ?? '—'}</strong></div></div><div class="metric"><div><label>导航状态</label><strong>${esc(data.nav.status ?? '—')}</strong></div></div></div>
      <div class="monitor-grid"><section class="card"><h3>工单</h3><form id="work-order-form"><input name="title" placeholder="工单标题" required><input name="location" placeholder="位置（可选）"><button class="btn-primary">新建工单</button></form><div class="table-wrap"><table><thead><tr><th>编号</th><th>标题</th><th>位置</th><th>状态</th><th>操作</th></tr></thead><tbody>${orderRows}</tbody></table></div></section><aside class="card"><h3>巡检点</h3><ul>${pointRows}</ul><h3>最近时间线</h3><ul>${timelineRows}</ul></aside></div></section>`;
    this._content.querySelector('#work-order-form')?.addEventListener('submit', async event => {
      event.preventDefault(); const form = new FormData(event.currentTarget);
      try { await window._api.createWorkOrder({ title: form.get('title'), location: form.get('location') }); await this.init(); }
      catch (error) { this._showActionError(`新建工单失败：${error.message}`); }
    });
    this._content.querySelectorAll('[data-update-order]').forEach(button => button.addEventListener('click', async () => {
      const id = button.dataset.updateOrder; const status = this._content.querySelector(`[data-order-status="${CSS.escape(id)}"]`).value;
      try { await window._api.updateWorkOrder(id, { status }); await this.init(); }
      catch (error) { this._showActionError(`更新工单失败：${error.message}`); }
    }));
  }
  _showActionError(message) {
    const node = document.createElement('p'); node.className = 'action-error'; node.textContent = message;
    this._content?.querySelector('.view-container')?.prepend(node);
  }
}
if (typeof module !== 'undefined' && module.exports) module.exports = { PatrolView };
