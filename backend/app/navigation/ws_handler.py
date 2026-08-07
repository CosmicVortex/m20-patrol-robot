"""WebSocket handler for navigation control."""

from __future__ import annotations

import logging
from typing import Any

from backend.app.navigation.service import NavigationService

logger = logging.getLogger(__name__)


class NavigationWebSocketHandler:
    """Handle navigation WebSocket messages."""

    def __init__(self, nav_service: NavigationService) -> None:
        self._nav_service = nav_service

    async def handle_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Handle navigation WebSocket messages."""
        action = message.get("action")

        if action == "authorize":
            operator = message.get("operator", "web_operator")
            note = message.get("note", "")
            return self._nav_service.authorize(operator, note)

        if action == "deauthorize":
            return self._nav_service.deauthorize()

        if action == "send_navigation":
            pos_x = message.get("pos_x", 0.0)
            pos_y = message.get("pos_y", 0.0)
            pos_z = message.get("pos_z", 0.0)
            angle_yaw = message.get("angle_yaw", 0.0)
            map_id = message.get("map_id", 1)
            return self._nav_service.send_navigation(pos_x, pos_y, pos_z, angle_yaw, map_id)

        if action == "cancel_navigation":
            return self._nav_service.cancel_navigation()

        if action == "get_status":
            return self._nav_service.get_status()

        if action == "get_audit_log":
            return {"audit_log": self._nav_service.audit_log}

        return {"status": "error", "message": f"Unknown action: {action}"}
