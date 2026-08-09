"""Response formatting and error handling for M20 API.

Provides consistent JSON error/success wrappers and HTTP status mapping.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from http.server import BaseHTTPRequestHandler
from typing import Any, Optional

try:
    from datetime import UTC
except ImportError:  # Python 3.8
    UTC = timezone.utc

logger = logging.getLogger(__name__)


class StatusCode(Enum):
    OK = "ok"
    ERROR = "error"
    BLOCKED = "blocked"
    UNAUTHORIZED = "unauthorized"
    NOT_FOUND = "not_found"
    UNVERIFIED = "unverified"
    CONFIGURED = "configured"
    STALE = "stale"


@dataclass(frozen=True)
class ApiResponse:
    status: str
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    code: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            object.__setattr__(self, "timestamp", datetime.now(UTC).isoformat())


class ApiFormatter:
    """Formats API responses consistently."""

    @staticmethod
    def success(data: dict[str, Any] | None = None, code: str = "ok") -> dict[str, Any]:
        response = ApiResponse(status="success", data=data, code=code)
        return asdict(response)

    @staticmethod
    def error(message: str, code: str = "error") -> dict[str, Any]:
        response = ApiResponse(status="error", error=message, code=code)
        return asdict(response)

    @staticmethod
    def send_response(
        handler: BaseHTTPRequestHandler,
        status_code: int,
        body: dict[str, Any],
    ) -> None:
        """Send JSON response with proper headers."""
        handler.send_response(status_code)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("X-Content-Type-Options", "nosniff")
        handler.end_headers()
        handler.wfile.write(json.dumps(body, ensure_ascii=False).encode("utf-8"))

    @staticmethod
    def send_error(
        handler: BaseHTTPRequestHandler,
        status_code: int,
        message: str,
        code: str = "error",
    ) -> None:
        """Send standardized error response."""
        body = ApiFormatter.error(message, code)
        ApiFormatter.send_response(handler, status_code, body)

    @staticmethod
    def send_json(
        handler: BaseHTTPRequestHandler,
        status_code: int,
        data: dict[str, Any],
    ) -> None:
        """Send success response."""
        body = ApiFormatter.success(data)
        ApiFormatter.send_response(handler, status_code, body)


class RequestContext:
    """Holds request-level context for handlers."""

    def __init__(
        self,
        method: str,
        path: str,
        client_address: tuple[str, int],
        timestamp: datetime | None = None,
        user: Any = None,
    ) -> None:
        self.method = method
        self.path = path
        self.client_address = client_address
        self.timestamp = timestamp or datetime.now(UTC)
        self.user = user

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "path": self.path,
            "client": self.client_address[0],
            "timestamp": self.timestamp.isoformat(),
            "user": self.user.username if self.user else None,
        }
