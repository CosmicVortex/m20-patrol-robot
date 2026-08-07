"""Real-time dashboard with basic_server status connection.

Connects to AOS basic_server TCP 30001 for read-only status streaming.
Navigation/motion control remains disabled by default.
"""

from __future__ import annotations

import html
import json
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from backend.app.robot.telemetry import TelemetryAdapter, ConnectionConfig


@dataclass(frozen=True)
class DashboardConfig:
    host: str = "127.0.0.1"
    port: int = 8080
    aos_host: str = "10.21.31.103"  # 已确认 AOS 地址
    aos_port: int = 30001
    required_firmware_version: str = "V1.1.8"  # 最低固件版本要求
    video_enabled: bool = True  # 视频接入已授权
    navigation_enabled: bool = False  # 导航需手动放行


class RealTimeDashboard:
    """Dashboard that connects to real AOS basic_server for status."""

    def __init__(self, config: DashboardConfig) -> None:
        self.config = config
        self._adapter: TelemetryAdapter | None = None
        self._lock = threading.Lock()
        self._running = False

    def start(self) -> None:
        """Start dashboard with real AOS connection."""
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
        """Stop dashboard and close connection."""
        self._running = False
        if self._adapter:
            self._adapter.stop()
            self._adapter = None

    def get_status_payload(self) -> dict[str, Any]:
        """Get current status payload."""
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
        """Render HTML dashboard page."""
        payload = self.get_status_payload()
        is_real = payload.get("source") == "REAL"
        is_connected = payload.get("connected", False)
        
        # Extract status data
        basic = payload.get("data", {}).get("basic", {})
        motion = payload.get("data", {}).get("motion", {})
        device = payload.get("data", {}).get("device", {})
        errors = payload.get("data", {}).get("errors", [])
        
        # Build status display
        status_html = self._render_status_section(payload, basic, motion, device, errors)
        
        # Build video section
        video_html = self._render_video_section()
        
        # Build header badge
        if is_real and is_connected:
            badge = '<span class="badge" style="border-color:var(--accent);color:var(--accent)">REAL / CONTROL OFF</span>'
        elif is_real:
            badge = '<span class="badge" style="border-color:var(--warn);color:var(--warn)">REAL / RECONNECTING</span>'
        else:
            badge = '<span class="badge">SIMULATED / CONTROL OFF</span>'
        
        # Build note
        if is_real and is_connected:
            note = '<p class="note" style="border-color:var(--accent)">连接 AOS basic_server 成功。状态数据实时接收中。</p>'
        elif is_real:
            note = '<p class="note" style="border-color:var(--warn)">正在重连 AOS basic_server...</p>'
        else:
            note = '<p class="note">该页面不会连接机器人、不发送心跳、不下发导航，也不会把模拟数据标为真实状态。</p>'

        return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>M20 巡逻状态</title>
<style>
:root {{ color-scheme: dark; --ink:#d9e3e7; --muted:#85959c; --panel:#111b20; --line:#26363e; --accent:#56ddad; --warn:#ffc24a; --bg:#071116; }}
* {{ box-sizing:border-box; }} body {{ margin:0; font-family:"Noto Sans SC","Source Han Sans SC",sans-serif; background:radial-gradient(circle at 70% 0,#14353b 0,transparent 30%),var(--bg); color:var(--ink); }}
header {{ padding:28px clamp(20px,5vw,72px); border-bottom:1px solid var(--line); display:flex; justify-content:space-between; gap:20px; align-items:center; }}
h1 {{ margin:0; font-size:clamp(22px,3vw,36px); letter-spacing:.04em; }} .badge {{ border:1px solid var(--warn); color:var(--warn); padding:7px 10px; font-weight:700; font-size:12px; letter-spacing:.12em; }}
main {{ max-width:1440px; margin:auto; padding:24px clamp(20px,5vw,72px) 56px; }} .grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; }}
.card {{ background:linear-gradient(145deg,#142229,#0d171c); border:1px solid var(--line); min-height:240px; padding:18px; }} h2 {{ margin:0 0 14px; font-size:15px; color:var(--muted); letter-spacing:.08em; }}
pre {{ white-space:pre-wrap; margin:0; color:#b9cbd0; font-size:13px; line-height:1.6; }}
.note {{ margin-top:18px; border-left:3px solid var(--accent); padding:12px 14px; color:var(--muted); background:#0d191d; }}
.status-row {{ display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid var(--line); }} .status-row:last-child {{ border-bottom:none; }}
.status-label {{ color:var(--muted); }} .status-value {{ font-weight:600; }}
.error-list {{ color:var(--warn); font-size:12px; }}
@media(max-width:760px) {{ .grid {{ grid-template-columns:1fr; }} header {{ align-items:flex-start; flex-direction:column; }} }}
</style>
</head>
<body>
<header><div><h1>M20 巡逻状态</h1><p>前后本体相机 · 状态只读 · 巡逻控制默认禁用</p></div>{badge}</header>
<main>
<section class="grid">
<article class="card"><h2>连接状态</h2>{status_html}</article>
<article class="card"><h2>异常列表</h2><pre>{self._render_errors(errors)}</pre></article>
</section>
{note}
</main>
<script>
setInterval(() => {{
    fetch('/api/v1/status/latest').then(r=>r.json()).then(v => {{
        document.querySelector('#status-content').innerHTML = v.data.message;
        const badge = document.querySelector('.badge');
        if (v.source === 'REAL' && v.connected) {{
            badge.textContent = 'REAL / CONTROL OFF';
            badge.style.borderColor = 'var(--accent)';
            badge.style.color = 'var(--accent)';
        }} else if (v.source === 'REAL') {{
            badge.textContent = 'REAL / RECONNECTING';
            badge.style.borderColor = 'var(--warn)';
            badge.style.color = 'var(--warn)';
        }} else {{
            badge.textContent = 'SIMULATED / CONTROL OFF';
            badge.style.borderColor = 'var(--warn)';
            badge.style.color = 'var(--warn)';
        }}
    }});
}}, 2000);
</script>
</body></html>"""

    def _render_status_section(self, payload: dict, basic: dict, motion: dict, 
                                device: dict, errors: list) -> str:
        """Render status HTML section."""
        rows = []
        
        # Connection info
        source = payload.get("source", "SIMULATED")
        connected = payload.get("connected", False)
        received_at = payload.get("received_at", "")
        age_ms = payload.get("age_ms")
        
        rows.append(self._status_row("数据源", source))
        rows.append(self._status_row("连接状态", "已连接" if connected else "未连接"))
        rows.append(self._status_row("最后更新", received_at or "—"))
        if age_ms is not None:
            rows.append(self._status_row("数据延迟", f"{age_ms}ms"))
        
        # Basic status
        if basic:
            rows.append(self._status_row("运动状态", str(basic.get("MotionState", "—"))))
            rows.append(self._status_row("步态", hex(basic.get("Gait", 0))))
            rows.append(self._status_row("充电状态", str(basic.get("Charge", "—"))))
        
        # Motion status
        if motion:
            rows.append(self._status_row("姿态", 
                f"Roll:{motion.get('Roll',0):.2f} "
                f"Pitch:{motion.get('Pitch',0):.2f} "
                f"Yaw:{motion.get('Yaw',0):.2f}"))
        
        # Device status
        if device:
            battery = device.get("BatteryStatus", {})
            if battery:
                left = battery.get("Left", {})
                right = battery.get("Right", {})
                rows.append(self._status_row("电量(左)", f"{left.get('BatteryLevel', '—')}%"))
                rows.append(self._status_row("电量(右)", f"{right.get('BatteryLevel', '—')}%"))
        
        return "\n".join(rows)

    def _render_errors(self, errors: list) -> str:
        """Render error list HTML."""
        if not errors:
            return "<span style='color:var(--accent)'>无异常</span>"
        return "\n".join(f'<span class="error-list">⚠ {e.get("errorCode", "?")}: {e.get("component", "?")}</span>' 
                        for e in errors[-5:])  # Show last 5 errors

    def _status_row(self, label: str, value: str) -> str:
        return f'<div class="status-row"><span class="status-label">{label}</span><span class="status-value">{html.escape(str(value))}</span></div>'

    def _render_video_section(self) -> str:
        return """<article class="card"><h2>视频流</h2><pre>前相机: rtsp://AOS_HOST:8554/video1<br>后相机: rtsp://AOS_HOST:8554/video2<br><br>状态: 待 GOS 实测确认编码格式与转码方案</pre></article>"""


def serve_dashboard(host: str = "127.0.0.1", port: int = 8080, 
                    aos_host: str = "10.21.31.103") -> None:
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
