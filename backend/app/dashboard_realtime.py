#!/usr/bin/env python3
"""
M20 巡逻机器人状态监控 - 完整版
连接真实 AOS basic_server，显示实时状态
"""

from __future__ import annotations

import html
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from backend.app.robot.telemetry import TelemetryAdapter, ConnectionConfig


@dataclass(frozen=True)
class DashboardConfig:
    host: str = "127.0.0.1"
    port: int = 8080
    aos_host: str = "10.21.31.103"
    aos_port: int = 30001
    required_firmware_version: str = "V1.1.8"
    video_enabled: bool = True
    navigation_enabled: bool = False


class RealTimeDashboard:
    """Dashboard that connects to real AOS basic_server for status."""

    def __init__(self, config: DashboardConfig) -> None:
        self.config = config
        self._adapter: TelemetryAdapter | None = None
        self._lock = threading.Lock()
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        telemetry_config = ConnectionConfig(
            host=self.config.aos_host,
            tcp_port=self.config.aos_port,
        )
        self._adapter = TelemetryAdapter(telemetry_config)
        self._adapter.start()

    def stop(self) -> None:
        self._running = False
        if self._adapter:
            self._adapter.stop()
            self._adapter = None

    def get_status_payload(self) -> dict[str, Any]:
        if self._adapter:
            return self._adapter.get_status_payload()
        return {
            "source": "SIMULATED",
            "connected": False,
            "control_enabled": False,
            "received_at": None,
            "age_ms": None,
            "data": {
                "robot": "M20 Pro",
                "navigation": "NOT_CONNECTED",
                "message": "Adapter not started.",
            },
        }

    def render_index(self) -> str:
        payload = self.get_status_payload()
        is_real = payload.get("source") == "REAL"
        is_connected = payload.get("connected", False)

        data = payload.get("data") or {}
        basic = data.get("basic", {})
        motion = data.get("motion", {})
        device = data.get("device", {})
        errors = data.get("errors", [])

        # Status rows
        rows = []
        rows.append(self._row("数据源", payload.get("source", "SIMULATED")))
        rows.append(self._row("连接状态", "已连接" if is_connected else "未连接", is_connected))
        rows.append(self._row("最后更新", str(payload.get("received_at", "—")) if payload.get("received_at") else "—"))
        if payload.get("age_ms") is not None:
            rows.append(self._row("数据延迟", f"{payload['age_ms']}ms"))

        rows.append(self._row("运动状态", self._motion_label(basic.get("MotionState"))))
        rows.append(self._row("步态", self._gait_label(basic.get("Gait"))))
        rows.append(self._row("充电状态", self._charge_label(basic.get("Charge"))))

        # Battery
        battery = device.get("BatteryStatus", {}) or {}
        left = battery.get("Left", {}) or {}
        right = battery.get("Right", {}) or {}
        left_pct = left.get("BatteryLevel")
        right_pct = right.get("BatteryLevel")

        # Errors
        error_html = ""
        if errors:
            error_items = []
            for e in errors[-5:]:
                code = e.get("errorCode", "?")
                comp = e.get("component", e.get("message", "?"))
                error_items.append(f'<span class="err"><span class="err-code">{code}</span> {html.escape(str(comp))}</span>')
            error_html = "<div class='errs'>" + "".join(error_items) + "</div>"
        else:
            error_html = '<span class="ok">无异常</span>'

        # Badge
        if is_real and is_connected:
            badge = '<span class="badge badge--ok">REAL / CONTROL OFF</span>'
            note = '<p class="note">连接 AOS basic_server 成功。状态数据实时接收中。</p>'
        elif is_real:
            badge = '<span class="badge badge--warn">REAL / RECONNECTING</span>'
            note = '<p class="note">正在重连 AOS basic_server...</p>'
        else:
            badge = '<span class="badge">SIMULATED / CONTROL OFF</span>'
            note = '<p class="note">该页面不会连接机器人、不发送心跳、不下发导航，也不会把模拟数据标为真实状态。</p>'

        return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>M20 巡逻状态</title>
<style>
:root {{
    color-scheme: dark;
    --ink: #d9e3e7;
    --muted: #85959c;
    --panel: #111b20;
    --line: #26363e;
    --accent: #4a9fd4;
    --warn: #ffc24a;
    --err: #ff6b6b;
    --bg: #071116;
}}
* {{ box-sizing:border-box; }}
body {{
    margin:0;
    font-family:"Noto Sans SC","Source Han Sans SC",-apple-system,sans-serif;
    background:radial-gradient(circle at 70% 0,#14353b 0,transparent 40%),var(--bg);
    color:var(--ink);
    min-height:100vh;
    line-height:1.6;
}}
/* Focus styles for accessibility */
:focus-visible {{
    outline:2px solid var(--accent);
    outline-offset:2px;
    border-radius:4px;
}}
header {{
    padding: 28px clamp(20px, 5vw, 72px);
    border-bottom: 1px solid var(--line);
    display: flex;
    justify-content: space-between;
    gap: 20px;
    align-items: center;
}}
h1 {{
    margin: 0;
    font-size: clamp(22px, 3vw, 32px);
    font-weight: 600;
    letter-spacing: -0.01em;
}}
h1 small {{
    display: block;
    font-size: 13px;
    font-weight: 400;
    color: var(--muted);
    margin-top: 4px;
    letter-spacing: 0;
}}
.badge {{
    border: 1px solid var(--line);
    color: var(--muted);
    padding: 6px 12px;
    font-weight: 600;
    font-size: 12px;
    letter-spacing: 0.08em;
    border-radius: 20px;
    background: var(--panel);
}}
.badge--ok {{ border-color: var(--accent); color: var(--accent); }}
.badge--warn {{ border-color: var(--warn); color: var(--warn); }}
main {{
    max-width: 1440px;
    margin: auto;
    padding: 24px clamp(20px, 5vw, 72px) 56px;
}}
.grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
}}
.card {{
    background: linear-gradient(145deg, #142229, #0d171c);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 20px;
    transition: border-color 0.15s, background 0.15s;
}}
.card:hover {{
    border-color: #3d414a;
    background: linear-gradient(145deg, #18282e, #101c22);
}}
.card h2 {{
    margin: 0 0 16px;
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.card h2::before {{
    content: "";
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent);
    opacity: 0.6;
}}
.row {{
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid var(--line);
    font-size: 13px;
}}
.row:last-child {{ border-bottom: none; }}
.row .label {{ color: var(--muted); }}
.row .value {{ font-weight: 500; font-variant-numeric: tabular-nums; }}
.row .value.ok {{ color: var(--accent); }}
.row .value.warn {{ color: var(--warn); }}
.row .value.err {{ color: var(--err); }}
.metrics {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-top: 4px;
}}
.metric {{
    background: var(--bg);
    border-radius: 8px;
    padding: 14px;
}}
.metric .num {{
    font-size: 26px;
    font-weight: 600;
    line-height: 1;
    margin-bottom: 6px;
    font-variant-numeric: tabular-nums;
}}
.metric .lbl {{
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
.prog {{ margin-top: 10px; }}
.prog-label {{
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    margin-bottom: 6px;
    color: var(--muted);
}}
.prog-bar {{
    height: 4px;
    background: var(--bg);
    border-radius: 2px;
    overflow: hidden;
}}
.prog-fill {{
    height: 100%;
    background: var(--accent);
    border-radius: 2px;
    transition: width 0.4s ease;
}}
.prog-fill.warn {{ background: var(--warn); }}
.prog-fill.err {{ background: var(--err); }}
.errs {{ display: flex; flex-direction: column; gap: 6px; }}
.err {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: rgba(255, 107, 107, 0.08);
    border-radius: 6px;
    border-left: 3px solid var(--err);
    font-size: 12px;
}}
.err-code {{
    font-family: "SF Mono", Monaco, monospace;
    color: var(--err);
    font-weight: 500;
    font-size: 11px;
}}
.ok {{ color: var(--accent); font-size: 13px; }}
.note {{
    margin-top: 18px;
    border-left: 3px solid var(--accent);
    padding: 12px 14px;
    color: var(--muted);
    background: #0d191d;
    border-radius: 0 8px 8px 0;
    font-size: 13px;
    line-height: 1.6;
}}
@media (max-width: 760px) {{
    .grid {{ grid-template-columns: 1fr; }}
    header {{ align-items: flex-start; flex-direction: column; }}
}}
</style>
</head>
<body>
<header>
    <div>
        <h1>M20 巡逻状态<small>前后本体相机 · 状态只读 · 巡逻控制默认禁用</small></h1>
    </div>
    {badge}
</header>
<main>
<section class="grid">
    <article class="card">
        <h2>连接状态</h2>
        <div id="status-content">{"".join(rows)}</div>
    </article>
    <article class="card">
        <h2>姿态数据</h2>
        <div class="metrics">
            <div class="metric"><div class="num">{motion.get('Roll', 0):.1f}</div><div class="lbl">Roll °</div></div>
            <div class="metric"><div class="num">{motion.get('Pitch', 0):.1f}</div><div class="lbl">Pitch °</div></div>
            <div class="metric"><div class="num">{motion.get('Yaw', 0):.1f}</div><div class="lbl">Yaw °</div></div>
            <div class="metric"><div class="num">{motion.get('Height', '—')}</div><div class="lbl">Height mm</div></div>
        </div>
    </article>
    <article class="card">
        <h2>电量</h2>
        <div class="prog">
            <div class="prog-label"><span>左电池</span><span>{left_pct if left_pct is not None else '—'}%</span></div>
            <div class="prog-bar"><div class="prog-fill" style="width:{left_pct or 0}%"></div></div>
        </div>
        <div class="prog" style="margin-top:14px">
            <div class="prog-label"><span>右电池</span><span>{right_pct if right_pct is not None else '—'}%</span></div>
            <div class="prog-bar"><div class="prog-fill" style="width:{right_pct or 0}%"></div></div>
        </div>
    </article>
    <article class="card" style="grid-column: span 2;">
        <h2>异常列表</h2>
        {error_html}
    </article>
</section>
{note}
</main>
<script>
setInterval(() => {{
    fetch('/api/v1/status/latest').then(r=>r.json()).then(v => {{
        const d = v.data || {{}};
        const b = d.basic || {{}};
        const m = d.motion || {{}};
        const dev = d.device || {{}};
        const errs = d.errors || [];

        // Badge
        const badge = document.querySelector('.badge');
        if (v.source === 'REAL' && v.connected) {{
            badge.className = 'badge badge--ok';
            badge.textContent = 'REAL / CONTROL OFF';
        }} else if (v.source === 'REAL') {{
            badge.className = 'badge badge--warn';
            badge.textContent = 'REAL / RECONNECTING';
        }} else {{
            badge.className = 'badge';
            badge.textContent = 'SIMULATED / CONTROL OFF';
        }}

        // Status
        const rows = [
            ['数据源', v.source || '—'],
            ['连接状态', v.connected ? '已连接' : '未连接', v.connected],
            ['最后更新', v.received_at || '—'],
            ['运动状态', _motion(b.MotionState)],
            ['步态', _gait(b.Gait)],
            ['充电状态', _charge(b.Charge)],
        ];
        if (v.age_ms != null) rows.push(['数据延迟', v.age_ms + 'ms']);
        document.getElementById('status-content').innerHTML = rows.map(r =>
            '<div class="row"><span class="label">' + r[0] + '</span><span class="value' + (r[2] === true ? ' ok' : r[2] === false ? ' err' : '') + '">' + htmlEscape(String(r[1])) + '</span></div>'
        ).join('');

        // Metrics
        const nums = document.querySelectorAll('.metric .num');
        if (nums[0]) nums[0].textContent = (m.Roll || 0).toFixed(1);
        if (nums[1]) nums[1].textContent = (m.Pitch || 0).toFixed(1);
        if (nums[2]) nums[2].textContent = (m.Yaw || 0).toFixed(1);
        if (nums[3]) nums[3].textContent = m.Height ?? '—';

        // Battery
        const bat = (dev.BatteryStatus || {{}});
        const leftP = bat.Left?.BatteryLevel ?? 0;
        const rightP = bat.Right?.BatteryLevel ?? 0;
        const fills = document.querySelectorAll('.prog-fill');
        if (fills[0]) {{ fills[0].style.width = leftP + '%'; fills[0].className = 'prog-fill' + (leftP < 20 ? ' err' : leftP < 40 ? ' warn' : ''); }}
        if (fills[1]) {{ fills[1].style.width = rightP + '%'; fills[1].className = 'prog-fill' + (rightP < 20 ? ' err' : rightP < 40 ? ' warn' : ''); }}
        const pl = document.querySelectorAll('.prog-label span:last-child');
        if (pl[0]) pl[0].textContent = leftP + '%';
        if (pl[1]) pl[1].textContent = rightP + '%';

        // Errors
        const errEl = document.querySelector('.card:nth-child(4) > div');
        if (errEl) {{
            if (!errs.length) {{
                errEl.innerHTML = '<span class="ok">无异常</span>';
            }} else {{
                errEl.innerHTML = errs.slice(-5).map(e =>
                    '<div class="err"><span class="err-code">' + htmlEscape(String(e.errorCode || '?')) + '</span> ' + htmlEscape(String(e.component || e.message || '?')) + '</div>'
                ).join('');
            }}
        }}
    }});
}}, 2000);

function _motion(s) {{ const m = {{0:'静止',1:'站立',2:'行走',3:'慢跑',4:'上下楼',5:'摔倒'}}; return m[s] ?? String(s ?? 0); }}
function _gait(g) {{ const m = {{4097:'基础标准',4098:'高台标准',12290:'平地敏捷',12291:'楼梯敏捷'}}; return m[g] ?? ('0x' + String(g ?? 0).toUpperCase()); }}
function _charge(c) {{ const m = {{0:'未充电',1:'充电中',2:'已充满',3:'充电异常'}}; return m[c] ?? String(c ?? 0); }}
function htmlEscape(s) {{ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }}
</script>
</body></html>"""

    def _row(self, label: str, value: str | None, ok: bool = False) -> str:
        cls = " ok" if ok else ""
        cls = " err" if value == "未连接" else cls
        safe_value = str(value) if value is not None else "—"
        return f'<div class="row"><span class="label">{html.escape(label)}</span><span class="value{cls}">{html.escape(safe_value)}</span></div>'

    def _motion_label(self, state: int) -> str:
        m = {0: "静止", 1: "站立", 2: "行走", 3: "慢跑", 4: "上下楼", 5: "摔倒"}
        return m.get(state, str(state))

    def _gait_label(self, gait: int) -> str:
        m = {0x1001: "基础标准", 0x1002: "高台标准", 0x3002: "平地敏捷", 0x3003: "楼梯敏捷"}
        return m.get(gait, f"0x{gait:04X}" if gait else "—")

    def _charge_label(self, charge: int) -> str:
        m = {0: "未充电", 1: "充电中", 2: "已充满", 3: "充电异常"}
        return m.get(charge, str(charge))

    def _render_errors(self, errors: list) -> str:
        if not errors:
            return '<span style="color:var(--accent)">无异常</span>'
        return "\n".join(
            f'<span class="err"><span class="err-code">{html.escape(str(e.get("errorCode", "?")))}</span> {html.escape(str(e.get("component", e.get("message", "?"))))}</span>'
            for e in errors[-5:]
        )


def serve_dashboard(host: str = "127.0.0.1", port: int = 8080, aos_host: str = "10.21.31.103") -> None:
    """Serve the real-time dashboard."""
    if host != "127.0.0.1":
        raise ValueError("dashboard may bind only to 127.0.0.1")
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("port must be an integer from 1 to 65535")

    config = DashboardConfig(host=host, port=port, aos_host=aos_host)
    dashboard = RealTimeDashboard(config)
    dashboard.start()

    try:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path in ("/", "/index.html"):
                    body = dashboard.render_index().encode()
                    self._send(200, "text/html; charset=utf-8", body)
                elif self.path == "/api/v1/status/latest":
                    payload = dashboard.get_status_payload()
                    body = json.dumps(payload, ensure_ascii=False).encode()
                    self._send(200, "application/json", body)
                else:
                    self._send(404, "text/plain; charset=utf-8", b"not found\n")

            def log_message(self, format: str, *args: object) -> None:
                del format, args
                return

            def _send(self, status: int, content_type: str, body: bytes) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

        ThreadingHTTPServer((host, port), Handler).serve_forever()
    finally:
        dashboard.stop()
