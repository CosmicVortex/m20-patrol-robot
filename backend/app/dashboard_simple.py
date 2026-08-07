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
    <title>M20 巡逻机器人状态监控</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            background: #0a0a0a;
            color: #00ff00;
            padding: 20px;
            min-height: 100vh;
        }
        .header {
            border-bottom: 2px solid #00ff00;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .status-panel {
            background: #1a1a1a;
            border: 1px solid #00ff00;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .error { color: #ff0000; }
        .success { color: #00ff00; }
        .warning { color: #ffff00; }
        pre {
            background: #0d0d0d;
            padding: 10px;
            overflow-x: auto;
            border-left: 3px solid #00ff00;
            font-size: 12px;
        }
        .refresh-note {
            color: #888;
            font-size: 12px;
            margin-top: 10px;
        }
        h1 { font-size: 24px; }
        h2 { font-size: 16px; margin-bottom: 10px; color: #00ff00; }
    </style>
</head>
<body>
    <div class="header">
        <h1>M20 巡逻机器人状态监控</h1>
        <p>Python 3.8 兼容版 | 无外部依赖 | 简化模式</p>
    </div>

    <div class="status-panel">
        <h2>实时状态</h2>
        <div id="status">正在加载...</div>
        <p class="refresh-note">每 2 秒自动刷新</p>
    </div>

    <div class="status-panel">
        <h2>系统信息</h2>
        <div id="info">加载中...</div>
    </div>

    <script>
        async function fetchStatus() {
            try {
                const response = await fetch('/api/v1/status/latest');
                const data = await response.json();
                document.getElementById('status').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                const statusDiv = document.getElementById('status');
                if (data.source === 'REAL') {
                    statusDiv.className = 'success';
                } else if (data.source === 'SIMULATED') {
                    statusDiv.className = 'warning';
                } else {
                    statusDiv.className = 'error';
                }
            } catch (e) {
                document.getElementById('status').innerHTML = '<span class="error">错误: ' + e.message + '</span>';
            }
        }
        async function fetchInfo() {
            try {
                const response = await fetch('/api/v1/health');
                const data = await response.json();
                document.getElementById('info').innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            } catch (e) {
                document.getElementById('info').innerHTML = '<span class="error">无法获取系统信息</span>';
            }
        }
        fetchStatus();
        fetchInfo();
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
            "data": {
                "robot": "M20 Pro",
                "navigation": "NOT_CONNECTED",
                "basic": {"MotionState": 0, "Gait": 0, "Charge": 0},
                "motion": {"Roll": 0, "Pitch": 0, "Yaw": 0},
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
