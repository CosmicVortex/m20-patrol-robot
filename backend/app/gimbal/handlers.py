"""Gimbal API handlers for M20 Pro."""

from __future__ import annotations

import logging
from typing import Any, Optional
from http.server import BaseHTTPRequestHandler

from backend.app.api.handlers import BaseHandler
from backend.app.gimbal.adapter import SoarGimbalAdapter, GimbalConfig

logger = logging.getLogger(__name__)


class BaseGimbalHandler(BaseHandler):
    """Base handler for gimbal endpoints."""

    def _get_gimbal(self) -> Optional[SoarGimbalAdapter]:
        """Get gimbal adapter from request."""
        return getattr(self, '_gimbal', None)


class GimbalStateHandler(BaseGimbalHandler):
    """GET /api/v1/gimbal/state"""

    def do_GET(self) -> None:
        gimbal = self._get_gimbal()
        if not gimbal or not gimbal.connected:
            self.send_json_response(200, {"connected": False, "message": "云台未连接"})
            return

        state = gimbal.get_state()
        self.send_json_response(200, state)


class GimbalMoveHandler(BaseGimbalHandler):
    """POST /api/v1/gimbal/move"""

    def do_POST(self) -> None:
        auth = self._authenticate()
        if not auth:
            return
        if auth.role != "admin":
            self.send_error_response(403, "需要管理员权限")
            return

        gimbal = self._get_gimbal()
        if not gimbal or not gimbal.connected:
            self.send_error_response(503, "云台未连接")
            return

        data = self._parse_json_body()
        direction = data.get("direction", "stop")
        speed = data.get("speed", 5)

        if gimbal.move_direction(direction, speed):
            self.send_json_response(200, {"status": "ok", "direction": direction, "speed": speed})
        else:
            self.send_error_response(500, "云台控制失败")


class GimbalZoomHandler(BaseGimbalHandler):
    """POST /api/v1/gimbal/zoom"""

    def do_POST(self) -> None:
        auth = self._authenticate()
        if not auth:
            return
        if auth.role != "admin":
            self.send_error_response(403, "需要管理员权限")
            return

        gimbal = self._get_gimbal()
        if not gimbal or not gimbal.connected:
            self.send_error_response(503, "云台未连接")
            return

        data = self._parse_json_body()
        action = data.get("action", "in")
        level = data.get("level", 5)

        if action == "in":
            ok = gimbal.zoom(9)
        elif action == "out":
            ok = gimbal.zoom(10)
        else:
            ok = gimbal.zoom_to(level)

        if ok:
            self.send_json_response(200, {"status": "ok", "action": action})
        else:
            self.send_error_response(500, "变倍控制失败")


class GimbalAngleHandler(BaseGimbalHandler):
    """POST /api/v1/gimbal/angle"""

    def do_POST(self) -> None:
        auth = self._authenticate()
        if not auth:
            return
        if auth.role != "admin":
            self.send_error_response(403, "需要管理员权限")
            return

        gimbal = self._get_gimbal()
        if not gimbal or not gimbal.connected:
            self.send_error_response(503, "云台未连接")
            return

        data = self._parse_json_body()
        yaw = data.get("yaw", 0)
        pitch = data.get("pitch", 0)

        if gimbal.set_angle(yaw, pitch):
            self.send_json_response(200, {"status": "ok", "yaw": yaw, "pitch": pitch})
        else:
            self.send_error_response(500, "角度设置失败")


class GimbalDeviceInfoHandler(BaseGimbalHandler):
    """GET /api/v1/gimbal/device/info"""

    def do_GET(self) -> None:
        gimbal = self._get_gimbal()
        if not gimbal:
            self.send_json_response(200, {"connected": False, "message": "云台未配置"})
            return

        info = gimbal.get_device_info()
        self.send_json_response(200, info)


class GimbalVideoHandler(BaseGimbalHandler):
    """GET /api/v1/gimbal/video"""

    def do_GET(self) -> None:
        gimbal = self._get_gimbal()
        if not gimbal:
            self.send_json_response(200, {"urls": {}, "message": "云台未配置"})
            return

        urls = gimbal.get_video_urls()
        self.send_json_response(200, {"urls": urls})


class GimbalScanHandler(BaseGimbalHandler):
    """GET /api/v1/gimbal/scan - Discover gimbal devices"""

    def do_GET(self) -> None:
        gimbal = self._get_gimbal()
        if not gimbal:
            self.send_error_response(500, "云台适配器未初始化")
            return

        # Trigger scan
        discovered = gimbal.scan()

        if discovered:
            # Auto-connect to first discovered device
            gimbal.auto_connect()
            self.send_json_response(200, {
                "discovered": discovered,
                "connected": gimbal.connected,
                "host": gimbal.config.host,
            })
        else:
            self.send_json_response(200, {
                "discovered": [],
                "connected": False,
                "message": "未发现云台设备",
            })
