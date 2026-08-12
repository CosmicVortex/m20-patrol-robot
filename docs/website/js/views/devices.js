/**
 * DevicesView - 设备管理视图
 * 
 * 功能：
 * - 机器狗档案
 * - 充电桩管理
 * - 门禁系统
 * - 环境传感器
 */
class DevicesView {
  constructor() {
    this._content = null;
  }
  
  async init() {
    this._content = document.querySelector('#view-devices');
    if (!this._content) return;
    
    await this._loadDevices();
  }
  
  destroy() {
    this._content = null;
  }
  
  render() {
    this._loadDevices();
  }

  async _loadDevices() {
    const devices = window._state.get('devices') || [];
    const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    
    let html = `
      <div class="card">
        <h3>设备列表</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>编号</th>
                <th>类型</th>
                <th>名称</th>
                <th>位置</th>
                <th>IP地址</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
    `;
    
    if (devices.length === 0) {
      html += '<tr><td colspan="7" style="text-align:center;color:var(--color-text-muted);padding:var(--space-8)">暂无设备数据，请添加设备</td></tr>';
    } else {
      devices.forEach(device => {
        const statusClass = device.status === 'online' ? 'ok' : device.status === 'offline' ? 'blocked' : 'warn';
        const statusText = device.status === 'online' ? '在线' : device.status === 'offline' ? '离线' : '故障';
        
        html += `
          <tr>
            <td>${esc(device.id)}</td>
            <td>${esc(device.type || '—')}</td>
            <td>${esc(device.name || '—')}</td>
            <td>${esc(device.location || '—')}</td>
            <td>${esc(device.ip_address || '—')}</td>
            <td><span class="status-badge ${statusClass}">${statusText}</span></td>
            <td>
              <button class="btn" data-edit-device="${esc(device.id)}">编辑</button>
              <button class="btn btn-danger" data-delete-device="${esc(device.id)}">删除</button>
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
      <div class="card" style="margin-top:var(--space-4)">
        <h3>添加设备</h3>
        <form id="add-device-form">
          <div class="form-row">
            <div class="form-group">
              <label>设备编号</label>
              <input type="text" name="id" class="input" placeholder="例如：DEV-001" required>
            </div>
            <div class="form-group">
              <label>设备类型</label>
              <select name="type" class="input">
                <option value="robot">机器狗</option>
                <option value="gimbal">云台</option>
                <option value="charger">充电桩</option>
                <option value="access_control">门禁</option>
                <option value="sensor">环境传感器</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>设备名称</label>
              <input type="text" name="name" class="input" placeholder="例如：数尔云台SR-UPA810T609">
            </div>
            <div class="form-group">
              <label>安装位置</label>
              <input type="text" name="location" class="input" placeholder="例如：机器狗顶部">
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>IP地址</label>
              <input type="text" name="ip_address" class="input" placeholder="例如：10.21.31.108">
            </div>
            <div class="form-group">
              <label>厂商</label>
              <input type="text" name="manufacturer" class="input" placeholder="例如：数尔">
            </div>
          </div>
          <button type="submit" class="btn btn-primary">添加设备</button>
        </form>
      </div>
    `;
    
    this._content.innerHTML = html;
    
    // 绑定事件
    document.getElementById('add-device-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = new FormData(e.target);
      try {
        await window._api.addDevice({
          id: form.get('id'),
          type: form.get('type'),
          name: form.get('name'),
          location: form.get('location'),
          ip_address: form.get('ip_address'),
          manufacturer: form.get('manufacturer')
        });
        await this._loadDevices();
      } catch (err) {
        alert(`添加设备失败: ${err.message}`);
      }
    });
    
    document.querySelectorAll('[data-delete-device]').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('确认删除该设备？')) return;
        try {
          await window._api.deleteDevice(btn.dataset.deleteDevice);
          await this._loadDevices();
        } catch (err) {
          alert(`删除设备失败: ${err.message}`);
        }
      });
    });
  }
}

if (typeof module !== 'undefined' && module.exports) module.exports = { DevicesView };