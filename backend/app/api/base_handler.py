"""Base HTTP handler for M20 Web service.

Provides common request handling, authentication, and response formatting.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

try:
    from datetime import UTC
except ImportError:  # Python 3.8
    from datetime import timezone
    UTC = timezone.utc

from http.server import BaseHTTPRequestHandler

from backend.app.auth.middleware import AuthMiddleware, AuthRequiredError, AuthResult
from backend.app.auth.store import UserStore
from backend.app.api.response import ApiFormatter, RequestContext
from backend.app.robot.telemetry import TelemetryAdapter
from backend.app.navigation.service import NavigationService
from backend.app.config import WebServiceConfig
from backend.app.gimbal.adapter import SoarGimbalAdapter
from backend.app.video.stream_manager import VideoStreamManager

logger = logging.getLogger(__name__)


class BaseHandler(BaseHTTPRequestHandler):
    """Base HTTP handler with auth and response formatting."""

    # Class-level dependencies injected by router
    auth_middleware: Optional[AuthMiddleware] = None
    telemetry_adapter: Optional[TelemetryAdapter] = None
    user_store: Optional[UserStore] = None
    nav_service: Optional[NavigationService] = None
    config: Optional[WebServiceConfig] = None
    gimbal_adapter: Optional[SoarGimbalAdapter] = None
    video_manager: Optional[VideoStreamManager] = None
    server_instance: Any = None  # Reference to M20WebServer instance

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
