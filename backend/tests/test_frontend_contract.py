"""Frontend contract tests that run against the shipped static assets."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[2]
WEB = ROOT / "docs" / "website"


def run_node(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_index_has_one_executable_application_entrypoint():
    html = (WEB / "index.html").read_text(encoding="utf-8")

    assert '<script src="js/app.js"></script>' in html
    assert html.count('<script src="js/app.js"></script>') == 1
    assert html.index('<script src="js/app.js"></script>') > html.index('id="main-app"')


def test_api_service_unwraps_success_and_uses_canonical_work_order_route():
    script = r"""
const { ApiService } = require('./docs/website/js/api-service.js');
const state = { get: () => null, set: () => {}, updateWorkOrders: value => global.updated = value };
const api = new ApiService(state);
let calls = [];
global.fetch = async (url, options = {}) => {
  calls.push([url, options.method || 'GET']);
  if (url.endsWith('/work-orders')) {
    return { ok: true, status: 200, json: async () => ({ status: 'success', data: { orders: [{ id: 'WO-1' }] } }) };
  }
  throw new Error('unexpected URL ' + url);
};
(async () => {
  const listed = await api.fetchWorkOrders();
  const created = await api.createWorkOrder({ title: '检查消防通道' });
  if (listed.orders[0].id !== 'WO-1') process.exit(2);
  if (created.orders[0].id !== 'WO-1') process.exit(3);
  if (calls[1][0] !== '/api/v1/work-orders' || calls[1][1] !== 'POST') process.exit(4);
})().catch(error => { console.error(error); process.exit(1); });
"""

    result = run_node(script)

    assert result.returncode == 0, result.stderr


def test_state_manager_reads_wrapped_login_response_and_real_position_fields():
    script = r"""
const { StateManager } = require('./docs/website/js/state-manager.js');
const state = new StateManager();
global.fetch = async (url) => {
  if (url.endsWith('/auth/login')) {
    return { ok: true, json: async () => ({ status: 'success', data: { username: 'admin', role: 'admin' } }) };
  }
  throw new Error('unexpected URL ' + url);
};
(async () => {
  const user = await state.login('admin', '123456');
  state.updateTelemetry({
    source: 'REAL', connected: true,
    data: { battery_percent: 72, position: { pos_x: 1.25, pos_y: -0.5, location: 3 } },
    inspection_stats: {}
  });
  if (user.username !== 'admin' || state.get('user.role') !== 'admin') process.exit(2);
  if (state.get('robot.position.pos_x') !== 1.25) process.exit(3);
  if (state.get('robot.location') !== 3) process.exit(4);
})().catch(error => { console.error(error); process.exit(1); });
"""

    result = run_node(script)

    assert result.returncode == 0, result.stderr


def test_dashboard_never_assigns_rtsp_url_to_html_video():
    source = (WEB / "js" / "views" / "dashboard.js").read_text(encoding="utf-8")

    assert "videoEl.src = src.rtsp_url" not in source


def test_dashboard_uses_browser_playback_endpoint():
    source = (WEB / "js" / "views" / "dashboard.js").read_text(encoding="utf-8")
    assert "videoEl.src = config.playback_url" in source
    assert "videoEl.src = src.rtsp_url" not in source


def test_server_websocket_frames_are_unmasked():
    source = (ROOT / "backend" / "app" / "websocket" / "upgrade.py").read_text(encoding="utf-8")
    assert "0x80 | length" not in source
    assert "0x81, 0x7E" in source


def test_websocket_pong_frames_are_unmasked_and_limited():
    source = (ROOT / "backend" / "app" / "websocket" / "upgrade.py").read_text(encoding="utf-8")
    assert "bytes([0x8A, len(payload)])" in source
    assert "0x80 | len(payload)" not in source


def test_app_initializes_router_after_login_without_duplicate_global_polling():
    source = (WEB / "js" / "app.js").read_text(encoding="utf-8")
    # Auto-login: check router initialization and app display
    assert "window._router.init()" in source
    assert "style.display = ''" in source
    assert "setInterval(async () =>" not in source


def test_emergency_stop_reports_server_command_result():
    source = (WEB / "js" / "app.js").read_text(encoding="utf-8")
    emergency_block = source[
        source.index("window.handleEmergencyStop"):source.index("// ── 云台管理")
    ]

    assert "command_sent" in emergency_block
    assert "throw new Error" in emergency_block
