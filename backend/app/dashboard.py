"""Read-only local dashboard for the M20 patrol application.

The module intentionally does not connect to AOS/NOS, open a robot-control socket,
or issue any navigation/motion command. It only serves an explicit simulated status
until a separately verified real client is integrated.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import datetime, timezone
# Python 3.8 compatibility: UTC was added in Python 3.11
try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


@dataclass(frozen=True)
class DashboardServer:
    title: str = "M20 Patrol Dashboard / Read-only"
    front_hls_url: str = "/streams/front/index.m3u8"
    rear_hls_url: str = "/streams/rear/index.m3u8"

    def status_payload(self) -> dict[str, Any]:
        return {
            "source": "SIMULATED",
            "connected": False,
            "control_enabled": False,
            "received_at": datetime.now(UTC).isoformat(),
            "age_ms": None,
            "data": {
                "robot": "M20 Pro",
                "navigation": "NOT_CONNECTED",
                "message": "Real AOS/NOS connection has not been enabled.",
            },
        }

    def render_index(self) -> str:
        title = html.escape(self.title)
        front_url = html.escape(self.front_hls_url, quote=True)
        rear_url = html.escape(self.rear_hls_url, quote=True)
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ color-scheme: dark; --ink:#d9e3e7; --muted:#85959c; --panel:#111b20; --line:#26363e; --accent:#56ddad; --warn:#ffc24a; --bg:#071116; }}
* {{ box-sizing:border-box; }} body {{ margin:0; font-family:"Noto Sans SC","Source Han Sans SC",sans-serif; background:radial-gradient(circle at 70% 0,#14353b 0,transparent 30%),var(--bg); color:var(--ink); }}
header {{ padding:28px clamp(20px,5vw,72px); border-bottom:1px solid var(--line); display:flex; justify-content:space-between; gap:20px; align-items:center; }}
h1 {{ margin:0; font-size:clamp(22px,3vw,36px); letter-spacing:.04em; }} .badge {{ border:1px solid var(--warn); color:var(--warn); padding:7px 10px; font-weight:700; font-size:12px; letter-spacing:.12em; }}
main {{ max-width:1440px; margin:auto; padding:24px clamp(20px,5vw,72px) 56px; }} .grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; }}
.card {{ background:linear-gradient(145deg,#142229,#0d171c); border:1px solid var(--line); min-height:240px; padding:18px; }} h2 {{ margin:0 0 14px; font-size:15px; color:var(--muted); letter-spacing:.08em; }}
.video {{ min-height:300px; display:grid; place-items:center; border:1px dashed #3e515a; color:var(--muted); position:relative; overflow:hidden; }} .video::before {{ content:""; position:absolute; inset:0; background:linear-gradient(135deg,transparent 48%,#1c343c 49%,transparent 50%); opacity:.3; }}
video {{ width:100%; height:100%; object-fit:cover; position:absolute; inset:0; }} .placeholder {{ z-index:1; text-align:center; max-width:28rem; padding:20px; }} pre {{ white-space:pre-wrap; margin:0; color:#b9cbd0; font-size:13px; line-height:1.6; }}
.note {{ margin-top:18px; border-left:3px solid var(--accent); padding:12px 14px; color:var(--muted); background:#0d191d; }}
@media(max-width:760px) {{ .grid {{ grid-template-columns:1fr; }} header {{ align-items:flex-start; flex-direction:column; }} }}
</style>
</head>
<body>
<header><div><h1>{title}</h1><p>前后本体相机 · 状态只读 · 巡逻控制默认禁用</p></div><span class="badge">SIMULATED / CONTROL OFF</span></header>
<main>
<section class="grid">
<article class="card"><h2>前向本体相机</h2><div class="video" data-camera="front"><video muted autoplay playsinline data-hls-src="{front_url}"></video><div class="placeholder">等待 GOS 现场验证并启动共享 HLS/WebRTC 视频管线。<br>当前不会直接拉取或修改 AOS 视频服务。</div></div></article>
<article class="card"><h2>后向本体相机</h2><div class="video" data-camera="rear"><video muted autoplay playsinline data-hls-src="{rear_url}"></video><div class="placeholder">后相机通道预留。实际 RTSP 编码、延迟和浏览器兼容性尚待 GOS 实测。</div></div></article>
<article class="card"><h2>机器人状态</h2><pre id="status">Loading status/latest …</pre></article>
<article class="card"><h2>巡逻安全状态</h2><pre>控制开关：关闭
导航：未连接
照片来源：前向本体相机优先
异常策略：暂停并等待现场操作员</pre></article>
</section>
<p class="note">该页面不会连接机器人、不发送心跳、不下发导航，也不会把模拟数据标为真实状态。真实状态和视频必须在 GOS 上完成设备、版本、网络和安全验证后再接入。</p>
</main>
<script>
fetch('/api/v1/status/latest').then(r=>r.json()).then(v=>document.querySelector('#status').textContent=JSON.stringify(v,null,2)).catch(e=>document.querySelector('#status').textContent='STATUS UNAVAILABLE: '+e);
</script>
</body></html>"""


def serve_dashboard(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Serve the simulated dashboard on loopback only."""
    if host != "127.0.0.1":
        raise ValueError("dashboard may bind only to 127.0.0.1")
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("port must be an integer from 1 to 65535")
    dashboard = DashboardServer()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/", "/index.html"):
                self._send(200, "text/html; charset=utf-8", dashboard.render_index().encode())
            elif self.path == "/api/v1/status/latest":
                self._send(200, "application/json", json.dumps(dashboard.status_payload()).encode())
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
