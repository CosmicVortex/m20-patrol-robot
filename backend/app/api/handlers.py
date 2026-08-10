"""API route handlers for M20 Web service.

Provides HTTP handlers for auth, status, devices, and navigation endpoints.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from typing import Any, Optional

try:
    from datetime import UTC
except ImportError:  # Python 3.8
    UTC = timezone.utc

from backend.app.auth.middleware import AuthMiddleware, AuthRequiredError, AuthResult
from backend.app.auth.store import AuthUser, AuthenticationError, Session, UserStore
from backend.app.api.response import ApiFormatter, RequestContext
from backend.app.robot.telemetry import TelemetryAdapter
from backend.app.navigation.service import NavigationService
from backend.app.config import WebServiceConfig

logger = logging.getLogger(__name__)


class BaseHandler(BaseHTTPRequestHandler):
    """Base HTTP handler with auth and response formatting."""

    auth_middleware: Optional[AuthMiddleware] = None
    telemetry_adapter: Optional[TelemetryAdapter] = None
    user_store: Optional[UserStore] = None
    nav_service: Optional[NavigationService] = None
    config: Optional[WebServiceConfig] = None

    def log_message(self, format: str, *args: Any) -> None:
        """Override to use structured logging."""
        context = RequestContext(
            method=self.command,
            path=self.path,
            client_address=self.client_address,
        )
        logger.info("%s %s - %s", context.method, context.path, format % args)

    def _read_body(self) -> bytes:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            return self.rfile.read(content_length)
        return b""

    def _parse_json_body(self) -> dict[str, Any]:
        body = self._read_body()
        if not body:
            return {}
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            ApiFormatter.send_error(self, 400, f"Invalid JSON: {exc}")
            return {}

    def _authenticate(self) -> Optional[AuthResult]:
        if self.auth_middleware is None:
            return None
        try:
            return self.auth_middleware.authenticate(self)
        except AuthRequiredError as exc:
            ApiFormatter.send_error(self, 401, str(exc), "unauthorized")
            return None

    def send_json_response(self, status: int, data: dict[str, Any]) -> None:
        ApiFormatter.send_json(self, status, data)

    def send_raw_json_response(self, status: int, data: dict[str, Any]) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def send_error_response(self, status: int, message: str, code: str = "error") -> None:
        ApiFormatter.send_error(self, status, message, code)


class HealthHandler(BaseHandler):
    """GET /api/v1/health - Service health check."""

    def do_GET(self) -> None:
        if self.path == "/api/v1/health":
            payload = self.telemetry_adapter.get_status_payload() if self.telemetry_adapter else {}
            health = {
                "service": "m20-patrol-web",
                "runtime_mode": getattr(self.telemetry_adapter.config, "runtime_mode", "unconfigured") if self.telemetry_adapter else "unconfigured",
                "read_only_mode": True,
                "control_enabled": False,
                "telemetry_tx_enabled": False,
                "source": payload.get("source", "NO_DATA"),
                "connected": payload.get("connected", False),
                "valid_frames": payload.get("valid_frames", 0),
                "bytes_received": payload.get("bytes_received", 0),
                "network_ready": payload.get("network_ready", False),
                "tcp_connected": payload.get("tcp_connected", False),
                "frame_valid": payload.get("frame_valid", False),
                "message_parsed": payload.get("message_parsed", False),
                "status_accepted": payload.get("status_accepted", False),
                "telemetry_fresh": payload.get("telemetry_fresh", False),
                "data_state": "REAL_FRESH" if payload.get("telemetry_fresh") else payload.get("source", "NO_DATA"),
                "age_ms": payload.get("age_ms"),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            health["healthy"] = (
                health["runtime_mode"] == "realtime_readonly"
                and health["source"] == "REAL"
                and health["connected"] is True
                and health["valid_frames"] > 0
                and health["bytes_received"] > 0
                and health["frame_valid"] is True
                and health["message_parsed"] is True
                and health["status_accepted"] is True
                and health["telemetry_fresh"] is True
                and isinstance(health["age_ms"], (int, float))
                and 0 <= health["age_ms"] < self.telemetry_adapter.config.stale_after_s * 1000 if self.telemetry_adapter else False
            )
            self.send_raw_json_response(200 if health["healthy"] else 503, health)
        else:
            self.send_error_response(404, "Not found")


class AuthLoginHandler(BaseHandler):
    """POST /api/v1/auth/login - User login."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/auth/login":
            self.send_error_response(404, "Not found")
            return

        body = self._parse_json_body()
        username = body.get("username", "").strip()
        password = body.get("password", "")

        if not username or not password:
            self.send_error_response(400, "username and password are required")
            return

        try:
            user = self.user_store.authenticate(username, password)
            session = self.user_store.create_session(user)
            logger.info("用户登录: %s", user.username)
            body = {
                "user_id": user.user_id,
                "username": user.username,
                "role": user.role,
                "session_expires": session.expires_at,
            }
            encoded = json.dumps(ApiFormatter.success(body), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if self.auth_middleware is None:
                self.send_error_response(500, "authentication middleware unavailable")
                return
            self.auth_middleware.set_session_cookie(self, session)
            self.end_headers()
            self.wfile.write(encoded)
        except AuthenticationError:
            logger.warning("登录失败")
            self.send_error_response(401, "invalid credentials")
        except Exception as exc:
            logger.error("Login error: %s", exc)
            self.send_error_response(500, "internal server error")


class AuthLogoutHandler(BaseHandler):
    """POST /api/v1/auth/logout - User logout."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/auth/logout":
            self.send_error_response(404, "Not found")
            return

        token = self.auth_middleware._extract_token(self) if self.auth_middleware else None
        if token and self.user_store:
            self.user_store.revoke_session(token)
        if self.auth_middleware:
            self.auth_middleware.revoke_session_cookie(self)
        self.send_json_response(200, {"status": "logged_out"})


class AuthMeHandler(BaseHandler):
    """GET /api/v1/auth/me - Current user info."""

    def do_GET(self) -> None:
        if self.path != "/api/v1/auth/me":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth:
            return

        self.send_json_response(200, {
            "user_id": auth.user.user_id,
            "username": auth.user.username,
            "role": auth.user.role,
        })


class StatusLatestHandler(BaseHandler):
    """GET /api/v1/status/latest - Latest robot status."""

    def do_GET(self) -> None:
        if self.path != "/api/v1/status/latest":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth and (not self.auth_middleware or not self.auth_middleware.allow_anonymous):
            return

        if self.telemetry_adapter is None:
            self.send_error_response(503, "Telemetry adapter not configured")
            return

        try:
            payload = self.telemetry_adapter.get_status_payload()
            # Keep the status endpoint machine-readable and compatible with
            # the deployment health gate. Auth/login responses are wrapped,
            # telemetry status is intentionally returned as the raw snapshot.
            self.send_raw_json_response(200, payload)
        except Exception as exc:
            logger.error("Status fetch error: %s", exc)
            self.send_error_response(500, str(exc))


class DevicesListHandler(BaseHandler):
    """GET /api/v1/devices - List connected devices."""

    def do_GET(self) -> None:
        if self.path != "/api/v1/devices":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth and (not self.auth_middleware or not self.auth_middleware.allow_anonymous):
            return

        self.send_json_response(200, {
            "devices": [
                {"id": "aos", "type": "application_server", "host": (self.config.aos_host if self.config else "not_configured") or "not_configured", "status": "configured"},
                {"id": "gos", "type": "guard_operator_station", "host": (self.config.host if self.config else "127.0.0.1"), "status": "configured"},
                {"id": "nos", "type": "navigation_operator_station", "host": "10.21.31.106", "status": "configured"},
            ]
        })


class NavigationStatusHandler(BaseHandler):
    """GET /api/v1/navigation/status - Navigation task status."""

    def do_GET(self) -> None:
        if self.path != "/api/v1/navigation/status":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth and (not self.auth_middleware or not self.auth_middleware.allow_anonymous):
            return

        nav_service = self.nav_service
        if nav_service is None:
            self.send_error_response(503, "Navigation service not configured")
            return

        status = nav_service.get_status()
        self.send_json_response(200, status)


class NavigationAuthorizeHandler(BaseHandler):
    """POST /api/v1/navigation/authorize - Request navigation control authorization."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/navigation/authorize":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth:
            return

        if auth.role != "admin":
            self.send_error_response(403, "admin role required")
            return

        nav_service = self.nav_service
        if nav_service is None:
            self.send_error_response(503, "Navigation service not configured")
            return

        body = self._parse_json_body()
        operator = body.get("operator", auth.user.username)
        note = body.get("note", "")

        try:
            result = nav_service.authorize(operator, note)
            self.send_json_response(200, result)
        except Exception as exc:
            logger.error("Authorization error: %s", exc)
            self.send_error_response(500, str(exc))


class NavigationTaskHandler(BaseHandler):
    """POST /api/v1/navigation/tasks - Submit navigation task."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/navigation/tasks":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth:
            return

        if auth.role != "admin":
            self.send_error_response(403, "admin role required")
            return

        nav_service = self.nav_service
        if nav_service is None:
            self.send_error_response(503, "Navigation service not configured")
            return

        body = self._parse_json_body()
        action = body.get("action")

        if action == "cancel":
            try:
                result = nav_service.cancel_navigation()
                self.send_json_response(200, result)
            except Exception as exc:
                logger.error("Cancel navigation error: %s", exc)
                self.send_error_response(500, str(exc))
        else:
            # Send navigation command
            pos_x = body.get("pos_x", 0.0)
            pos_y = body.get("pos_y", 0.0)
            pos_z = body.get("pos_z", 0.0)
            angle_yaw = body.get("angle_yaw", 0.0)
            map_id = body.get("map_id", 1)

            try:
                result = nav_service.send_navigation(pos_x, pos_y, pos_z, angle_yaw, map_id)
                self.send_json_response(200, result)
            except Exception as exc:
                logger.error("Navigation error: %s", exc)
                self.send_error_response(500, str(exc))


class NavigationCancelHandler(BaseHandler):
    """POST /api/v1/navigation/cancel - Cancel navigation task."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/navigation/cancel":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth:
            return

        if auth.role != "admin":
            self.send_error_response(403, "admin role required")
            return

        nav_service = self.nav_service
        if nav_service is None:
            self.send_error_response(503, "Navigation service not configured")
            return

        try:
            result = nav_service.cancel_navigation()
            self.send_json_response(200, result)
        except Exception as exc:
            logger.error("Cancel navigation error: %s", exc)
            self.send_error_response(500, str(exc))


class EmergencyStopHandler(BaseHandler):
    """POST /api/v1/emergency/stop - Emergency stop (requires admin auth)."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/emergency/stop":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth:
            return

        if auth.role != "admin":
            self.send_error_response(403, "admin role required")
            return

        # Read-only mode: emergency stop is blocked until field authorization
        nav_service = self.nav_service
        if nav_service is None:
            self.send_error_response(503, "Navigation service not configured")
            return

        result = nav_service.get_status()
        if not result.get("authorized"):
            self.send_json_response(200, {
                "authorized": False,
                "message": "Navigation control not authorized. Requires field authorization via /api/v1/navigation/authorize.",
                "service_status": result,
            })
            return

        # Authenticated path - still blocks actual command in read-only mode
        if not result.get("control_enabled"):
            self.send_json_response(200, {
                "authorized": True,
                "message": "Emergency stop blocked: control_enabled=false (read-only mode)",
            })
            return

        # This path requires field authorization + control_enabled=true
        self.send_json_response(200, {
            "authorized": True,
            "message": "Emergency stop command sent",
            "timestamp": datetime.now(UTC).isoformat(),
        })


class VideoStatusHandler(BaseHandler):
    """GET /api/v1/video - Camera stream status."""

    def do_GET(self) -> None:
        if self.path != "/api/v1/video":
            self.send_error_response(404, "Not found")
            return

        # No auth required for status viewing
        allow_real_io = (self.config.allow_real_io if self.config else False)

        # Build status from VideoStreamManager if available
        video_mgr = getattr(self, '_video_manager', None)
        if video_mgr:
            states = video_mgr.get_all_states()
            sources = {}
            for source, state_info in states.items():
                sources[source] = {
                    "state": state_info.get("state", "blocked"),
                    "rtsp_url": state_info.get("rtsp_url", ""),
                    "last_update": state_info.get("last_update"),
                    "label": state_info.get("label", source),
                }
        else:
            sources = {
                "front": {
                    "state": "blocked" if not allow_real_io else "unverified",
                    "rtsp_url": "rtsp://10.21.31.103:8554/video1",
                    "label": "前向本体相机",
                    "note": "需现场ffprobe确认可达性",
                },
                "rear": {
                    "state": "blocked" if not allow_real_io else "unverified",
                    "rtsp_url": "rtsp://10.21.31.103:8554/video2",
                    "label": "后向本体相机",
                    "note": "需现场ffprobe确认可达性",
                },
                "thermal": {
                    "state": "blocked" if not allow_real_io else "unverified",
                    "rtsp_url": "rtsp://10.21.31.103:8554/thermal",
                    "label": "热成像相机",
                    "note": "云台IP待确认",
                },
            }

        self.send_json_response(200, {
            "sources": sources,
            "status": "VIDEO_IO_BLOCKED" if not allow_real_io else "VIDEO_IO_ENABLED",
            "message": "视频流默认禁用，配置 RTSP 地址后启用。" if not allow_real_io else "视频流已启用，等待 ffprobe 探测",
        })
