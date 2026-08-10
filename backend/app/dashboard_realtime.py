#!/usr/bin/env python3
"""
M20 巡逻机器人状态监控 - 完整版
连接真实 AOS basic_server，显示实时状态
"""

from __future__ import annotations

import html
import json
import logging
import threading
import os
from dataclasses import dataclass
from datetime import datetime, timezone
try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from backend.app.robot.telemetry import TelemetryAdapter, ConnectionConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DashboardConfig:
    host: str = "127.0.0.1"
    port: int = 8080
    aos_host: str = ""
    aos_port: int = 30001
    required_firmware_version: str = "V1.1.8"
    video_enabled: bool = True
    navigation_enabled: bool = False
    runtime_mode: str = "simulated"
    read_only_mode: bool = True
    control_enabled: bool = False
    telemetry_tx_enabled: bool = False
    telemetry_receive_enabled: bool = True
    stale_after_s: float = 3.0

    def __post_init__(self) -> None:
        if type(self.read_only_mode) is not bool:
            raise ValueError("read_only_mode must be boolean")
        if type(self.control_enabled) is not bool:
            raise ValueError("control_enabled must be boolean")
        if type(self.telemetry_tx_enabled) is not bool:
            raise ValueError("telemetry_tx_enabled must be boolean")
        if self.stale_after_s <= 0:
            raise ValueError("stale_after_s must be positive")
        if self.telemetry_tx_enabled:
            raise ValueError("telemetry transmission is disabled in this release")
        if not self.read_only_mode or self.control_enabled:
            raise ValueError("dashboard requires read_only_mode=true and control_enabled=false")


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
        if self.config.runtime_mode not in {"simulated", "realtime", "realtime_readonly"}:
            raise ValueError("runtime_mode must be simulated, realtime, or realtime_readonly")
        if self.config.runtime_mode in {"realtime", "realtime_readonly"} and not self.config.aos_host:
            raise ValueError("realtime mode requires a field-confirmed aos_host")
        if not self.config.read_only_mode or self.config.control_enabled:
            raise ValueError("dashboard requires read_only_mode=true and control_enabled=false")

        self._running = True
        logger.info(
            "READ_ONLY_MODE=%s CONTROL_ENABLED=%s M20_RUNTIME_MODE=%s "
            "ALLOW_ROBOT_TELEMETRY_TX=%s TARGET_HOST=%s TARGET_PORT=%s",
            str(self.config.read_only_mode).lower(),
            str(self.config.control_enabled).lower(),
            self.config.runtime_mode,
            str(self.config.telemetry_tx_enabled).lower(),
            self.config.aos_host or "<unset>",
            self.config.aos_port,
        )
        telemetry_config = ConnectionConfig(
            host=self.config.aos_host,
            tcp_port=self.config.aos_port,
            runtime_mode=self.config.runtime_mode,
            read_only=self.config.read_only_mode,
            telemetry_tx_enabled=self.config.telemetry_tx_enabled,
            telemetry_receive_enabled=self.config.telemetry_receive_enabled,
            stale_after_s=self.config.stale_after_s,
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
            "source": "NO_DATA",
            "connected": False,
            "control_enabled": False,
            "received_at": None,
            "age_ms": None,
            "data": {
                "robot": "M20 Pro",
                "navigation": "NOT_CONNECTED",
                "message": "Adapter not started; no robot data is available.",
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

        rows.append(self._row("运动状态", self._motion_label(basic.get("motion_state"))))
        rows.append(self._row("步态", self._gait_label(basic.get("gait"))))
        rows.append(self._row("充电状态", self._charge_label(basic.get("charge"))))

        # Motion metrics (handle None safely)
        roll_val = motion.get('roll', 0)
        pitch_val = motion.get('pitch', 0)
        yaw_val = motion.get('yaw', 0)
        height_val = motion.get('height', '—')

        # Battery
        battery = device.get("BatteryStatus", {}) or {}
        left = battery.get("Left", {}) or {}
        right = battery.get("Right", {}) or {}
        left_pct = left.get("BatteryLevel")
        right_pct = right.get("BatteryLevel")

        # Navigation status
        nav_status = data.get("nav_status") or {}
        loop_count = nav_status.get("loop_count", 0)
        nav_status_val = nav_status.get("status", 0)
        nav_status_map = {0: "待命", 1: "导航中", 2: "已到达", 3: "异常", 4: "取消"}
        nav_label = nav_status_map.get(nav_status_val, str(nav_status_val))

        # Position
        position = data.get("position") or {}
        pos_x = position.get("pos_x")
        pos_y = position.get("pos_y")
        location = position.get("location")

        # Coverage stats
        coverage_rate = 0.0
        if position:
            has_pos = bool(position.get("pos_x") is not None or position.get("location"))
            is_moving = basic.get("motion_state", 0) in (2, 3, 4)
            if has_pos and is_moving:
                coverage_rate = 100.0
            elif has_pos:
                coverage_rate = 50.0

        # Error count
        anomaly_count = len(errors)
        if errors:
            error_items = []
            for e in errors[-5:]:
                if e is None:
                    continue
                code = e.get("error_code", "?")
                comp = e.get("component", e.get("message", "?"))
                error_items.append(f'<span class="err"><span class="err-code">{html.escape(str(code))}</span> {html.escape(str(comp))}</span>')
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
        <h1>M20 巡逻状态<small>前后本体相机 · 状态订阅 · 控制默认禁用</small></h1>
    </div>
    {badge}
</header>
<main>
<section class="grid">
    <article class="card">
        <h2>连接状态</h2>
        <div id="status-content">{" ".join(rows)}</div>
    </article>
    <article class="card">
        <h2>姿态数据</h2>
        <div class="metrics">
            <div class="metric"><div class="num">{roll_val if roll_val is not None else '—'}</div><div class="lbl">Roll °</div></div>
            <div class="metric"><div class="num">{pitch_val if pitch_val is not None else '—'}</div><div class="lbl">Pitch °</div></div>
            <div class="metric"><div class="num">{yaw_val if yaw_val is not None else '—'}</div><div class="lbl">Yaw °</div></div>
            <div class="metric"><div class="num">{height_val if height_val is not None else '—'}</div><div class="lbl">Height mm</div></div>
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
    <article class="card">
        <h2>导航状态</h2>
        <div class="metrics">
            <div class="metric"><div class="num">{loop_count}</div><div class="lbl">今日圈数</div></div>
            <div class="metric"><div class="num">{int(coverage_rate)}%</div><div class="lbl">覆盖率</div></div>
            <div class="metric" style="grid-column: span 2"><div class="num" style="font-size:18px">{nav_label}</div><div class="lbl">导航状态</div></div>
        </div>
        <div style="margin-top:12px;font-size:12px;color:var(--muted)">
            <div>位置: {f'{pos_x:.2f}, {pos_y:.2f}' if pos_x is not None and pos_y is not None else '—'}</div>
            <div>区域: {location or '未知'}</div>
        </div>
    </article>
    <article class="card">
        <h2>巡检统计</h2>
        <div class="metrics">
            <div class="metric"><div class="num">{anomaly_count}</div><div class="lbl">异常数</div></div>
            <div class="metric"><div class="num">{payload.get('message_count', 0)}</div><div class="lbl">消息数</div></div>
            <div class="metric" style="grid-column: span 2"><div class="num" style="font-size:18px">{payload.get('source', '—')}</div><div class="lbl">数据源</div></div>
        </div>
    </article>
    <article class="card" style="grid-column: span 2">
        <h2>异常列表</h2>
        {error_html}
    </article>
</section>
<div style="margin-top:20px;display:flex;align-items:center;gap:16px;padding:16px;background:var(--panel);border-radius:8px;border:1px solid var(--line)">
    <img src="robot-dog.jpg" alt="M20 Pro" style="width:80px;height:60px;object-fit:contain;background:#fff;border-radius:4px">
    <div>
        <div style="font-size:14px;font-weight:500;margin-bottom:4px">M20 Pro 巡逻机器狗</div>
        <div style="font-size:12px;color:var(--muted)">轮足复合结构 · 工业巡检级 · 实时状态订阅中</div>
    </div>
    <div style="margin-left:auto;text-align:right">
        <div style="font-size:12px;color:var(--muted)">当前任务</div>
        <div style="font-size:16px;font-weight:500;color:var(--accent)">{nav_label}</div>
    </div>
</div>
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
            ['运动状态', _motion(b.motion_state)],
            ['步态', _gait(b.gait)],
            ['充电状态', _charge(b.charge)],
        ];
        if (v.age_ms != null) rows.push(['数据延迟', v.age_ms + 'ms']);
        document.getElementById('status-content').innerHTML = rows.map(r =>
            '<div class="row"><span class="label">' + r[0] + '</span><span class="value' + (r[2] === true ? ' ok' : r[2] === false ? ' err' : '') + '">' + htmlEscape(String(r[1])) + '</span></div>'
        ).join('');

        // Metrics
        const nums = document.querySelectorAll('.metric .num');
        if (nums[0]) nums[0].textContent = (m.roll || 0).toFixed(1);
        if (nums[1]) nums[1].textContent = (m.pitch || 0).toFixed(1);
        if (nums[2]) nums[2].textContent = (m.yaw || 0).toFixed(1);
        if (nums[3]) nums[3].textContent = m.height ?? '—';

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
        const errEl = document.querySelector('.card:nth-child(6) > div');
        if (errEl) {{
            if (!errs.length) {{
                errEl.innerHTML = '<span class="ok">无异常</span>';
            }} else {{
                errEl.innerHTML = errs.slice(-5).map(e =>
                    '<div class="err"><span class="err-code">' + htmlEscape(String(e.error_code || '?')) + '</span> ' + htmlEscape(String(e.component || e.message || '?')) + '</div>'
                ).join('');
            }}
        }}

        // Navigation status
        const navEl = document.querySelector('.card:nth-child(4)');
        if (navEl) {{
            const nav = d.nav_status || {{}};
            const pos = d.position || {{}};
            const navStatusMap = {{0:'待命',1:'导航中',2:'已到达',3:'异常',4:'取消'}};
            const navLabel = navStatusMap[nav.status] || String(nav.status || 0);
            const metrics = navEl.querySelectorAll('.metric');
            if (metrics[0]) metrics[0].querySelector('.num').textContent = nav.loop_count || 0;
            if (metrics[1]) metrics[1].querySelector('.num').textContent = (v.inspection_stats?.coverage_rate ?? 0) + '%'; // coverage from inspection_stats
            if (metrics[2]) {{
                const n = metrics[2].querySelector('.num');
                n.textContent = navLabel;
                n.style.fontSize = '18px';
            }}
            const info = navEl.querySelector('div[style]');
            if (info) {{
                const px = pos.pos_x ?? '—';
                const py = pos.pos_y ?? '—';
                info.innerHTML = '<div>位置: ' + (px === '—' ? '—' : parseFloat(px).toFixed(2)) + ', ' + (py === '—' ? '—' : parseFloat(py).toFixed(2)) + '</div><div>区域: ' + htmlEscape(pos.location || '未知') + '</div>';
            }}
        }}

        // Inspection stats
        const statsEl = document.querySelector('.card:nth-child(5)');
        if (statsEl) {{
            const stats = v.inspection_stats || {{}};
            const metrics = statsEl.querySelectorAll('.metric');
            if (metrics[0]) metrics[0].querySelector('.num').textContent = stats.anomaly_count || 0;
            if (metrics[1]) metrics[1].querySelector('.num').textContent = v.message_count || 0;
            if (metrics[2]) {{
                const n = metrics[2].querySelector('.num');
                n.textContent = v.source || '—';
                n.style.fontSize = '18px';
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
            f'<span class="err"><span class="err-code">{html.escape(str(e.get("error_code", "?")))}</span> {html.escape(str(e.get("component", e.get("message", "?"))))}</span>'
            for e in errors[-5:]
        )


def serve_dashboard(
    host: str = "127.0.0.1",
    port: int = 8080,
    aos_host: str = "",
    runtime_mode: str = "simulated",
    read_only_mode: bool = True,
    control_enabled: bool = False,
    telemetry_tx_enabled: bool = False,
    telemetry_receive_enabled: bool = True,
    stale_after_s: float = 3.0,
    allowed_hosts: tuple[str, ...] | None = None,
) -> None:
    """Serve the real-time dashboard."""
    # Allow configurable binding hosts; default to localhost + GOS
    if allowed_hosts is None:
        allowed_hosts = ("127.0.0.1", "10.21.31.104")
    if host not in allowed_hosts:
        raise ValueError(f"dashboard may bind only to {allowed_hosts}")
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("port must be an integer from 1 to 65535")

    config = DashboardConfig(
        host=host,
        port=port,
        aos_host=aos_host or os.environ.get("M20_TARGET_HOST", ""),
        aos_port=int(os.environ.get("M20_TARGET_PORT", "30001")),
        runtime_mode=os.environ.get("M20_RUNTIME_MODE", runtime_mode),
        read_only_mode=read_only_mode,
        control_enabled=control_enabled,
        telemetry_tx_enabled=telemetry_tx_enabled,
        telemetry_receive_enabled=telemetry_receive_enabled,
        stale_after_s=float(os.environ.get("M20_STALE_AFTER_SECONDS", str(stale_after_s))),
    )
    if config.runtime_mode in {"realtime", "realtime_readonly"} and not config.aos_host:
        raise ValueError("realtime mode requires a field-confirmed aos_host")
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
                    payload["data_state"] = "REAL_FRESH" if payload.get("telemetry_fresh") else (
                        "REAL_STALE" if payload.get("source") == "STALE" else payload.get("source", "NO_DATA")
                    )
                    body = json.dumps(payload, ensure_ascii=False).encode()
                    self._send(200, "application/json", body)
                elif self.path == "/api/v1/health":
                    payload = dashboard.get_status_payload()
                    payload["data_state"] = "REAL_FRESH" if payload.get("telemetry_fresh") else (
                        "REAL_STALE" if payload.get("source") == "STALE" else payload.get("source", "NO_DATA")
                    )
                    health = {
                        "service": "m20-patrol-readonly",
                        "runtime_mode": dashboard.config.runtime_mode,
                        "read_only_mode": dashboard.config.read_only_mode,
                        "control_enabled": dashboard.config.control_enabled,
                        "telemetry_tx_enabled": dashboard.config.telemetry_tx_enabled,
                        "source": payload.get("source"),
                        "connected": payload.get("connected"),
                        "valid_frames": payload.get("valid_frames", 0),
                        "bytes_received": payload.get("bytes_received", 0),
                        "network_ready": payload.get("network_ready", False),
                        "tcp_connected": payload.get("tcp_connected", False),
                        "frame_valid": payload.get("frame_valid", False),
                        "message_parsed": payload.get("message_parsed", False),
                        "status_accepted": payload.get("status_accepted", False),
                        "telemetry_fresh": payload.get("telemetry_fresh", False),
                        "data_state": payload.get("data_state", payload.get("source", "NO_DATA")),
                        "age_ms": payload.get("age_ms"),
                    }
                    healthy = (
                        health["runtime_mode"] == "realtime_readonly"
                        and health["read_only_mode"] is True
                        and health["control_enabled"] is False
                        and health["telemetry_tx_enabled"] is False
                        and health["network_ready"] is True
                        and health["tcp_connected"] is True
                        and health["connected"] is True
                        and health["bytes_received"] > 0
                        and health["frame_valid"] is True
                        and health["valid_frames"] > 0
                        and health["source"] == "REAL"
                        and health["message_parsed"] is True
                        and health["status_accepted"] is True
                        and health["telemetry_fresh"] is True
                        and health["data_state"] == "REAL_FRESH"
                        and isinstance(health["age_ms"], (int, float))
                        and 0 <= health["age_ms"] < dashboard.config.stale_after_s * 1000
                    )
                    health["healthy"] = healthy
                    self._send(200 if healthy else 503, "application/json", json.dumps(health).encode())
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
