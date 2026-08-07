"""Web API for navigation control with manual authorization.

Navigation commands require explicit Web UI authorization before sending.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
# Python 3.8 compatibility: UTC was added in Python 3.11
try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc
from typing import Any

from backend.app.navigation.v010 import (
    SinglePointNavigation,
    NavigationSafetySnapshot,
    NavigationInterlockError,
)
from backend.app.robot.basic_client import BasicServerClient, BasicServerConfig
from backend.app.protocol.messages import PatrolMessage
from backend.app.robot.status import parse_status_message, StatusResult

logger = logging.getLogger(__name__)


@dataclass
class NavigationAuthorization:
    """Web UI authorization state for navigation."""
    authorized: bool = False
    authorized_at: str = ""
    authorized_by: str = ""
    authorization_note: str = ""


@dataclass
class NavigationAuditLog:
    """Audit log for navigation operations."""
    timestamp: str
    action: str  # "authorize", "send", "cancel", "error"
    details: str
    success: bool = False


class NavigationService:
    """Navigation control service with Web authorization."""

    def __init__(self, client: BasicServerClient, safety: NavigationSafetySnapshot) -> None:
        self._client = client
        self._safety = safety
        self._auth = NavigationAuthorization()
        self._audit_log: list[NavigationAuditLog] = []
        self._current_task_id: int = 0

    @property
    def is_authorized(self) -> bool:
        return self._auth.authorized

    @property
    def audit_log(self) -> list[NavigationAuditLog]:
        return list(self._audit_log)

    def authorize(self, operator: str, note: str = "") -> dict[str, Any]:
        """Authorize navigation control via Web UI."""
        self._auth = NavigationAuthorization(
            authorized=True,
            authorized_at=datetime.now(UTC).isoformat(),
            authorized_by=operator,
            authorization_note=note,
        )
        self._log("authorize", f"Operator: {operator}, Note: {note}", True)
        logger.info(f"Navigation authorized by {operator}")
        return {
            "status": "authorized",
            "operator": operator,
            "authorized_at": self._auth.authorized_at,
        }

    def deauthorize(self) -> dict[str, Any]:
        """Deauthorize navigation control."""
        self._auth = NavigationAuthorization()
        self._log("deauthorize", "Navigation control disabled", True)
        logger.info("Navigation deauthorized")
        return {"status": "deauthorized"}

    def send_navigation(self, pos_x: float, pos_y: float, pos_z: float = 0.0, 
                        angle_yaw: float = 0.0, map_id: int = 1) -> dict[str, Any]:
        """Send single-point navigation command."""
        if not self._auth.authorized:
            return {"status": "error", "message": "Navigation not authorized"}
        
        if not self._safety.control_enabled:
            return {"status": "error", "message": "Control not enabled"}
        
        if not self._safety.tcp_connected:
            return {"status": "error", "message": "Not connected to AOS"}

        try:
            nav = SinglePointNavigation(
                value=1,
                map_id=map_id,
                pos_x=pos_x,
                pos_y=pos_y,
                pos_z=pos_z,
                angle_yaw=angle_yaw,
            )
            msg = nav.to_message(self._safety, datetime.now(UTC).isoformat())
            
            self._current_task_id += 1
            task_id = self._current_task_id
            
            # Send message (this will connect to AOS)
            try:
                response = self._client.send_control(msg)
                self._log("send", f"Task {task_id}: navigate to ({pos_x}, {pos_y})", True)
                logger.info(f"Navigation task {task_id} sent")
                return {
                    "status": "sent",
                    "task_id": task_id,
                    "message": f"Navigation to ({pos_x}, {pos_y}) sent",
                }
            except Exception as e:
                self._log("send", f"Task {task_id}: failed - {e}", False)
                return {"status": "error", "message": str(e)}

        except NavigationInterlockError as e:
            self._log("send", f"Safety check failed: {e}", False)
            return {"status": "error", "message": str(e)}
        except Exception as e:
            self._log("send", f"Unexpected error: {e}", False)
            return {"status": "error", "message": str(e)}

    def cancel_navigation(self) -> dict[str, Any]:
        """Cancel current navigation task."""
        if not self._auth.authorized:
            return {"status": "error", "message": "Navigation not authorized"}
        
        if not self._safety.tcp_connected:
            return {"status": "error", "message": "Not connected to AOS"}

        try:
            from backend.app.navigation.v010 import build_cancel_navigation_message
            msg = build_cancel_navigation_message(self._safety, datetime.now(UTC).isoformat())
            
            self._client.send_control(msg)
            self._log("cancel", "Navigation cancelled", True)
            logger.info("Navigation cancelled")
            return {"status": "cancelled"}

        except Exception as e:
            self._log("cancel", f"Cancel failed: {e}", False)
            return {"status": "error", "message": str(e)}

    def get_status(self) -> dict[str, Any]:
        """Get navigation service status."""
        return {
            "authorized": self._auth.authorized,
            "authorized_at": self._auth.authorized_at,
            "authorized_by": self._auth.authorized_by,
            "authorization_note": self._auth.authorization_note,
            "control_enabled": self._safety.control_enabled,
            "tcp_connected": self._safety.tcp_connected,
            "current_task_id": self._current_task_id,
            "audit_log_count": len(self._audit_log),
        }

    def _log(self, action: str, details: str, success: bool) -> None:
        log = NavigationAuditLog(
            timestamp=datetime.now(UTC).isoformat(),
            action=action,
            details=details,
            success=success,
        )
        self._audit_log.append(log)
        # Keep only last 100 entries
        if len(self._audit_log) > 100:
            self._audit_log = self._audit_log[-100:]
