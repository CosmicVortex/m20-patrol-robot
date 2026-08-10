"""Gimbal API handlers for M20 Pro."""

from __future__ import annotations

import logging
from typing import Optional
from http.server import BaseHTTPRequestHandler

from backend.app.api.response import ApiFormatter
from backend.app.api.handlers import BaseHandler
from backend.app.gimbal.adapter import SoarGimbalAdapter, GimbalConfig

logger = logging.getLogger(__name__)


class GimbalStateHandler(BaseHandler):
    """GET /api/v1/gimbal/state - Get current gimbal state."""

    def do_GET(self) -> None:
        if self.path != "/api/v1/gimbal/state":
            self.send_error_response(404, "Not found")
            return

        gimbal: Optional[SoarGimbalAdapter] = getattr(self, '_gimbal', None)
        if gimbal is None:
            self.send_error_response(503, "Gimbal adapter not initialized")
            return

        state = gimbal.get_state()
        self.send_json_response(200, {
            "connected": gimbal._connected if hasattr(gimbal, '_connected') else False,
            "yaw": state.get("yaw", 0),
            "pitch": state.get("pitch", 0),
            "roll": state.get("roll", 0),
            "zoom": state.get("zoom", 1),
        })


class GimbalMoveHandler(BaseHandler):
    """POST /api/v1/gimbal/move - Move gimbal direction."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/gimbal/move":
            self.send_error_response(404, "Not found")
            return

        gimbal: Optional[SoarGimbalAdapter] = getattr(self, '_gimbal', None)
        if gimbal is None:
            self.send_error_response(503, "Gimbal adapter not initialized")
            return

        body = self._parse_json_body()
        direction = body.get("direction", "stop")
        speed = body.get("speed", 5)

        if direction not in ("up", "down", "left", "right", "stop"):
            self.send_error_response(400, "Invalid direction. Use: up/down/left/right/stop")
            return

        success = gimbal.move_direction(direction, speed)
        if success:
            logger.info("Gimbal moved: %s (speed=%d)", direction, speed)
            self.send_json_response(200, {"success": True, "direction": direction})
        else:
            self.send_error_response(500, "Failed to move gimbal")


class GimbalZoomHandler(BaseHandler):
    """POST /api/v1/gimbal/zoom - Zoom control."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/gimbal/zoom":
            self.send_error_response(404, "Not found")
            return

        gimbal: Optional[SoarGimbalAdapter] = getattr(self, '_gimbal', None)
        if gimbal is None:
            self.send_error_response(503, "Gimbal adapter not initialized")
            return

        body = self._parse_json_body()
        action = body.get("action", "in")  # in/out

        if action == "in":
            success = gimbal.zoom(9, speed=body.get("speed", 5))
        elif action == "out":
            success = gimbal.zoom(10, speed=body.get("speed", 5))
        elif action == "set":
            level = body.get("level", 5)
            success = gimbal.zoom_to(level)
        else:
            self.send_error_response(400, "Invalid action. Use: in/out/set")
            return

        if success:
            logger.info("Gimbal zoom: %s", action)
            self.send_json_response(200, {"success": True, "action": action})
        else:
            self.send_error_response(500, "Failed to zoom")


class GimbalAngleHandler(BaseHandler):
    """POST /api/v1/gimbal/angle - Set absolute angle."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/gimbal/angle":
            self.send_error_response(404, "Not found")
            return

        gimbal: Optional[SoarGimbalAdapter] = getattr(self, '_gimbal', None)
        if gimbal is None:
            self.send_error_response(503, "Gimbal adapter not initialized")
            return

        body = self._parse_json_body()
        yaw = body.get("yaw", 0)
        pitch = body.get("pitch", 0)

        success = gimbal.set_angle(yaw=yaw, pitch=pitch)
        if success:
            logger.info("Gimbal angle set: yaw=%s, pitch=%s", yaw, pitch)
            self.send_json_response(200, {"success": True, "yaw": yaw, "pitch": pitch})
        else:
            self.send_error_response(500, "Failed to set angle")


class GimbalDeviceInfoHandler(BaseHandler):
    """GET /api/v1/gimbal/device/info - Get gimbal device info."""

    def do_GET(self) -> None:
        if self.path != "/api/v1/gimbal/device/info":
            self.send_error_response(404, "Not found")
            return

        gimbal: Optional[SoarGimbalAdapter] = getattr(self, '_gimbal', None)
        if gimbal is None:
            self.send_error_response(503, "Gimbal adapter not initialized")
            return

        info = gimbal.get_device_info()
        self.send_json_response(200, info)


class GimbalVideoHandler(BaseHandler):
    """GET /api/v1/gimbal/video - Get gimbal video stream URLs."""

    def do_GET(self) -> None:
        if self.path != "/api/v1/gimbal/video":
            self.send_error_response(404, "Not found")
            return

        gimbal: Optional[SoarGimbalAdapter] = getattr(self, '_gimbal', None)
        if gimbal is None:
            self.send_error_response(503, "Gimbal adapter not initialized")
            return

        config = gimbal.config
        self.send_json_response(200, {
            "visible_light": config.rtsp_url,
            "thermal": config.thermal_rtsp_url,
            "gimbal_host": config.host,
            "gimbal_port": config.port,
        })
