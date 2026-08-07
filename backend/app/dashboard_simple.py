#!/usr/bin/env python3
"""
M20 巡逻机器人状态监控 - 简化版
适配 Python 3.8.10 环境，无外部依赖
"""

import http.server
import json
import socketserver
import sys
from datetime import datetime
from pathlib import Path

# Python 3.8 兼容性：UTC 在 3.11 才加入标准库
try:
    from datetime import UTC
except ImportError:
    UTC = None

sys.path.insert(0, str(Path(__file__).parent.parent))


class SimpleDashboardHandler(http.server.BaseHTTPRequestHandler):
    """简单的 HTTP 处理器，无需 fastapi/uvicorn"""

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self._get_html().encode('utf-8'))

        elif self.path == '/api/v1/status/latest':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            status = self._get_status()
            self.wfile.write(json.dumps(status, indent=2, ensure_ascii=False).encode('utf-8'))

        elif self.path == '/api/v1/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            health = {
                "status": "ok",
                "python_version": sys.version.split()[0],
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(health, indent=2).encode('utf-8'))

        else:
            self.send_error(404)

    def _get_html(self):
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>M20 巡逻机器人</title>
    <style>
        :root {
            --bg: #0d0f14;
            --surface: #14161a;
            --surface-hover: #1a1d22;
            --border: #2a2d34;
            --border-hover: #3d414a;
            --text: #e8eaed;
            --text-secondary: #9aa0a6;
            --text-muted: #5f6368;
            --accent: #3ea6ff;
            --accent-dim: rgba(62, 166, 255, 0.12);
            --success: #0d904f;
            --success-dim: rgba(13, 144, 79, 0.12);
            --warn: #f2a80c;
            --warn-dim: rgba(242, 168, 12, 0.12);
            --error: #d93025;
            --error-dim: rgba(217, 48, 37, 0.12);
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 16px;
            --transition: 150ms cubic-bezier(0.4, 0, 0.2, 1);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, "Segoe UI", "Noto Sans SC", "Microsoft YaHei", sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            line-height: 1.6;
        }

        /* Focus styles for accessibility */
        :focus-visible {
            outline: 2px solid var(--accent);
            outline-offset: 2px;
            border-radius: 4px;
        }
        }

        /* Layout */
        .layout {
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px 24px 48px;
        }

        /* Header */
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 20px 0 28px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 28px;
        }

        .header-left h1 {
            font-size: 22px;
            font-weight: 600;
            letter-spacing: -0.01em;
            margin-bottom: 4px;
        }

        .header-left p {
            font-size: 13px;
            color: var(--text-secondary);
        }

        /* Status Badge */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
            letter-spacing: 0.02em;
            border: 1px solid var(--border);
            color: var(--text-secondary);
            background: var(--surface);
        }

        .badge-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--text-muted);
        }

        .badge.connected .badge-dot {
            background: var(--success);
            box-shadow: 0 0 6px var(--success);
        }
        .badge.connected {
            border-color: var(--success);
            color: var(--success);
            background: var(--success-dim);
        }

        .badge.reconnecting .badge-dot {
            background: var(--warn);
            animation: pulse 1.5s ease-in-out infinite;
        }
        .badge.reconnecting {
            border-color: var(--warn);
            color: var(--warn);
            background: var(--warn-dim);
        }

        .badge.simulated .badge-dot {
            background: var(--text-muted);
        }
        .badge.simulated {
            border-color: var(--border);
            color: var(--text-muted);
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        /* Grid */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        /* Cards */
        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 20px;
            transition: border-color var(--transition), background var(--transition);
        }

        .card:hover {
            border-color: var(--border-hover);
            background: var(--surface-hover);
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
        }

        .card-title {
            font-size: 12px;
            font-weight: 500;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }

        .card-icon {
            width: 28px;
            height: 28px;
            border-radius: var(--radius-sm);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }

        /* Status Items */
        .status-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .status-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid var(--border);
        }

        .status-item:last-child {
            border-bottom: none;
        }

        .status-label {
            font-size: 13px;
            color: var(--text-secondary);
        }

        .status-value {
            font-size: 13px;
            font-weight: 500;
            color: var(--text);
            font-variant-numeric: tabular-nums;
        }

        .status-value.success { color: var(--success); }
        .status-value.warn { color: var(--warn); }
        .status-value.error { color: var(--error); }

        /* Metrics */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }

        .metric {
            background: var(--bg);
            border-radius: var(--radius-sm);
            padding: 14px;
        }

        .metric-value {
            font-size: 24px;
            font-weight: 600;
            color: var(--text);
            line-height: 1;
            margin-bottom: 6px;
            font-variant-numeric: tabular-nums;
        }

        .metric-label {
            font-size: 12px;
            color: var(--text-muted);
        }

        /* Progress Bar */
        .progress-container {
            margin-top: 8px;
        }

        .progress-bar {
            height: 4px;
            background: var(--bg);
            border-radius: 2px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            background: var(--accent);
            border-radius: 2px;
            transition: width 0.5s ease;
        }

        .progress-fill.success { background: var(--success); }
        .progress-fill.warn { background: var(--warn); }
        .progress-fill.error { background: var(--error); }

        /* Errors */
        .error-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .error-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            background: var(--error-dim);
            border-radius: var(--radius-sm);
            border-left: 3px solid var(--error);
            font-size: 12px;
        }

        .error-code {
            font-family: "SF Mono", Monaco, monospace;
            color: var(--error);
            font-weight: 500;
        }

        .error-msg {
            color: var(--text-secondary);
        }

        .empty-state {
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--success);
            font-size: 13px;
        }

        /* Info Panel */
        .info-panel {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 16px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
        }

        .info-text {
            font-size: 13px;
            color: var(--text-secondary);
        }

        .info-text strong {
            color: var(--text);
        }

        /* Refresh indicator */
        .refresh-indicator {
            position: fixed;
            bottom: 24px;
            right: 24px;
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 14px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 20px;
            font-size: 12px;
            color: var(--text-muted);
        }

        .refresh-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--accent);
            animation: blink 2s ease-in-out infinite;
        }

        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.2; }
        }

        /* Video placeholder */
        .video-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }

        .video-placeholder {
            aspect-ratio: 16/9;
            background: var(--bg);
            border-radius: var(--radius-sm);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 8px;
            color: var(--text-muted);
            font-size: 12px;
            border: 1px dashed var(--border);
        }

        .video-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* Responsive */
        @media (max-width: 640px) {
            .layout { padding: 16px 16px 40px; }
            .header { flex-direction: column; align-items: flex-start; gap: 12px; }
            .grid { grid-template-columns: 1fr; }
            .metrics-grid { grid-template-columns: 1fr; }
            .video-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="layout">
        <header class="header">
            <div class="header-left">
                <h1>M20 巡逻机器人</h1>
                <p>状态监控 · 只读模式 · 控制已禁用</p>
            </div>
            <div class="badge simulated" id="conn-badge">
                <span class="badge-dot"></span>
                <span id="conn-text">SIMULATED</span>
            </div>
        </header>

        <div class="grid">
            <!-- Connection Status -->
            <article class="card">
                <div class="card-header">
                    <span class="card-title">连接状态</span>
                    <div class="card-icon" style="background: var(--accent-dim); color: var(--accent);">⬡</div>
                </div>
                <div class="status-list">
                    <div class="status-item">
                        <span class="status-label">数据源</span>
                        <span class="status-value" id="source">—</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">连接状态</span>
                        <span class="status-value" id="connected">—</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">最后更新</span>
                        <span class="status-value" id="last-update">—</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">数据延迟</span>
                        <span class="status-value" id="latency">—</span>
                    </div>
                </div>
            </article>

            <!-- Basic Status -->
            <article class="card">
                <div class="card-header">
                    <span class="card-title">基础状态</span>
                    <div class="card-icon" style="background: var(--success-dim); color: var(--success);">◈</div>
                </div>
                <div class="status-list">
                    <div class="status-item">
                        <span class="status-label">运动状态</span>
                        <span class="status-value" id="motion-state">—</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">步态</span>
                        <span class="status-value" id="gait">—</span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">充电状态</span>
                        <span class="status-value" id="charge">—</span>
                    </div>
                </div>
            </article>

            <!-- Motion -->
            <article class="card">
                <div class="card-header">
                    <span class="card-title">姿态数据</span>
                    <div class="card-icon" style="background: var(--warn-dim); color: var(--warn);">△</div>
                </div>
                <div class="metrics-grid">
                    <div class="metric">
                        <div class="metric-value" id="roll">—</div>
                        <div class="metric-label">Roll (°)</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" id="pitch">—</div>
                        <div class="metric-label">Pitch (°)</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" id="yaw">—</div>
                        <div class="metric-label">Yaw (°)</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" id="height">—</div>
                        <div class="metric-label">高度 (mm)</div>
                    </div>
                </div>
            </article>

            <!-- Battery -->
            <article class="card">
                <div class="card-header">
                    <span class="card-title">电量</span>
                    <div class="card-icon" style="background: var(--accent-dim); color: var(--accent);">⚡</div>
                </div>
                <div class="progress-container">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span class="status-label">左电池</span>
                        <span class="status-value" id="battery-left">—</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="battery-left-bar" style="width: 0%"></div>
                    </div>
                </div>
                <div class="progress-container" style="margin-top: 14px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span class="status-label">右电池</span>
                        <span class="status-value" id="battery-right">—</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="battery-right-bar" style="width: 0%"></div>
                    </div>
                </div>
            </article>

            <!-- Errors -->
            <article class="card" style="grid-column: span 2;">
                <div class="card-header">
                    <span class="card-title">异常列表</span>
                    <div class="card-icon" style="background: var(--error-dim); color: var(--error);">⚠</div>
                </div>
                <div class="error-list" id="error-list">
                    <div class="empty-state">
                        <span>✓</span>
                        <span>无异常</span>
                    </div>
                </div>
            </article>

            <!-- Video -->
            <article class="card" style="grid-column: span 2;">
                <div class="card-header">
                    <span class="card-title">视频流</span>
                    <div class="card-icon" style="background: var(--border); color: var(--text-secondary);">◉</div>
                </div>
                <div class="video-grid">
                    <div class="video-placeholder">
                        <span style="font-size: 24px;">📷</span>
                        <span class="video-label">前相机</span>
                        <span style="font-size: 11px;">rtsp://AOS_HOST:8554/video1</span>
                    </div>
                    <div class="video-placeholder">
                        <span style="font-size: 24px;">📷</span>
                        <span class="video-label">后相机</span>
                        <span style="font-size: 11px;">rtsp://AOS_HOST:8554/video2</span>
                    </div>
                </div>
            </article>
        </div>

        <div class="info-panel">
            <span class="info-text">
                <strong>简化版模式</strong> — 当前未连接 AOS，显示模拟数据。连接真实设备后自动切换为实时状态。
            </span>
            <span class="info-text" style="color: var(--text-muted);">
                Python <span id="python-version">—</span>
            </span>
        </div>
    </div>

    <div class="refresh-indicator">
        <span class="refresh-dot"></span>
        <span>自动刷新 2s</span>
    </div>

    <script>
        const els = {
            source: document.getElementById('source'),
            connected: document.getElementById('connected'),
            lastUpdate: document.getElementById('last-update'),
            latency: document.getElementById('latency'),
            motionState: document.getElementById('motion-state'),
            gait: document.getElementById('gait'),
            charge: document.getElementById('charge'),
            roll: document.getElementById('roll'),
            pitch: document.getElementById('pitch'),
            yaw: document.getElementById('yaw'),
            height: document.getElementById('height'),
            batteryLeft: document.getElementById('battery-left'),
            batteryRight: document.getElementById('battery-right'),
            batteryLeftBar: document.getElementById('battery-left-bar'),
            batteryRightBar: document.getElementById('battery-right-bar'),
            errorList: document.getElementById('error-list'),
            badge: document.getElementById('conn-badge'),
            connText: document.getElementById('conn-text'),
            pythonVersion: document.getElementById('python-version')
        };

        const MOTION_MAP = { 0: '静止', 1: '站立', 2: '行走', 3: '慢跑', 4: '上下楼', 5: '摔倒' };
        const GAIT_MAP = { 0x1001: '基础标准', 0x1002: '高台标准', 0x3002: '平地敏捷', 0x3003: '楼梯敏捷' };
        const CHARGE_MAP = { 0: '未充电', 1: '充电中', 2: '已充满', 3: '充电异常' };

        function formatTime(iso) {
            if (!iso) return '—';
            const d = new Date(iso);
            return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        }

        function updateBadge(source, connected) {
            els.badge.className = 'badge';
            if (source === 'REAL' && connected) {
                els.badge.classList.add('connected');
                els.connText.textContent = 'REAL';
            } else if (source === 'REAL') {
                els.badge.classList.add('reconnecting');
                els.connText.textContent = 'RECONNECTING';
            } else {
                els.badge.classList.add('simulated');
                els.connText.textContent = 'SIMULATED';
            }
        }

        function updateBattery(level, barId, textId) {
            const pct = level || 0;
            const el = document.getElementById(textId);
            const bar = document.getElementById(barId);
            if (el) el.textContent = pct + '%';
            if (bar) {
                bar.style.width = pct + '%';
                bar.className = 'progress-fill' + (pct < 20 ? ' error' : pct < 40 ? ' warn' : ' success');
            }
        }

        function renderErrors(errors) {
            if (!errors || errors.length === 0) {
                els.errorList.innerHTML = '<div class="empty-state"><span>✓</span><span>无异常</span></div>';
                return;
            }
            els.errorList.innerHTML = errors.slice(-5).map(e =>
                `<div class="error-item">
                    <span class="error-code">${e.errorCode || '?'}</span>
                    <span class="error-msg">${e.component || e.message || '未知异常'}</span>
                </div>`
            ).join('');
        }

        async function fetchStatus() {
            try {
                const r = await fetch('/api/v1/status/latest');
                const d = await r.json();
                const data = d.data || {};
                const basic = data.basic || {};
                const motion = data.motion || {};
                const device = data.device || {};
                const errors = data.errors || [];

                els.source.textContent = d.source || '—';
                els.connected.textContent = d.connected ? '已连接' : '未连接';
                els.connected.className = 'status-value' + (d.connected ? ' success' : ' error');
                els.lastUpdate.textContent = formatTime(d.received_at);
                els.latency.textContent = d.age_ms != null ? d.age_ms + 'ms' : '—';

                els.motionState.textContent = MOTION_MAP[basic.MotionState] || String(basic.MotionState || 0);
                els.gait.textContent = GAIT_MAP[basic.Gait] || '0x' + (basic.Gait || 0).toString(16).toUpperCase();
                els.charge.textContent = CHARGE_MAP[basic.Charge] || '—';

                els.roll.textContent = (motion.Roll || 0).toFixed(1);
                els.pitch.textContent = (motion.Pitch || 0).toFixed(1);
                els.yaw.textContent = (motion.Yaw || 0).toFixed(1);
                els.height.textContent = motion.Height != null ? motion.Height : '—';

                const leftBat = device.BatteryStatus?.Left?.BatteryLevel || 0;
                const rightBat = device.BatteryStatus?.Right?.BatteryLevel || 0;
                updateBattery(leftBat, 'battery-left-bar', 'battery-left');
                updateBattery(rightBat, 'battery-right-bar', 'battery-right');

                renderErrors(errors);
                updateBadge(d.source, d.connected);
            } catch (e) {
                console.error('Fetch error:', e);
            }
        }

        async function fetchHealth() {
            try {
                const r = await fetch('/api/v1/health');
                const d = await r.json();
                if (d.python_version) els.pythonVersion.textContent = d.python_version;
            } catch (e) {}
        }

        fetchStatus();
        fetchHealth();
        setInterval(fetchStatus, 2000);
    </script>
</body>
</html>'''

    def _get_status(self):
        """返回模拟状态数据（简化版不连接真实设备）"""
        return {
            "source": "SIMULATED",
            "connected": False,
            "control_enabled": False,
            "received_at": None,
            "age_ms": None,
            "data": {
                "robot": "M20 Pro",
                "navigation": "NOT_CONNECTED",
                "basic": {"MotionState": 0, "Gait": 0x1001, "Charge": 0},
                "motion": {"Roll": 0.0, "Pitch": 0.0, "Yaw": 0.0, "Height": 320},
                "device": {
                    "BatteryStatus": {
                        "Left": {"BatteryLevel": 85},
                        "Right": {"BatteryLevel": 82}
                    }
                },
                "errors": []
            },
            "timestamp": datetime.now().isoformat(),
            "note": "简化版 - 未连接 AOS（Python 3.8 兼容模式）"
        }

    def log_message(self, format, *args):
        """静默日志"""
        pass


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def serve_dashboard(host="127.0.0.1", port=8080):
    server = ThreadedHTTPServer((host, port), SimpleDashboardHandler)
    print(f"{'='*50}")
    print(f"M20 巡逻机器人状态监控服务")
    print(f"{'='*50}")
    print(f"Python 版本: {sys.version.split()[0]}")
    print(f"服务地址: http://{host}:{port}/")
    print(f"健康检查: http://{host}:{port}/api/v1/health")
    print(f"状态 API: http://{host}:{port}/api/v1/status/latest")
    print(f"{'='*50}")
    print("按 Ctrl+C 停止服务")
    print(f"{'='*50}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.server_close()


if __name__ == "__main__":
    serve_dashboard()
