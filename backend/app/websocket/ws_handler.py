"""WebSocket handler for M20 Pro patrol robot.

Provides WebSocket endpoints for real-time video streaming and navigation control.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """Base WebSocket handler with auth and routing."""

    def __init__(self, web_socket_path: str) -> None:
        self._path = web_socket_path
        self._handlers: dict[str, Any] = {}

    def on(self, action: str, handler: Any) -> None:
        """Register a message handler for an action."""
        self._handlers[action] = handler

    async def handle_message(self, message: str) -> Optional[dict[str, Any]]:
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(message)
            action = data.get("action", "")
            if action in self._handlers:
                return await self._handlers[action](data)
            return {"type": "error", "message": f"Unknown action: {action}"}
        except json.JSONDecodeError:
            return {"type": "error", "message": "Invalid JSON"}


class VideoWebSocketHandler(WebSocketHandler):
    """Handle video stream WebSocket connections."""

    def __init__(self, manager: Any) -> None:
        super().__init__("/ws/video")
        self._manager = manager

        self.on("get_states", self._get_states)
        self.on("select_stream", self._select_stream)
        self.on("get_selected", self._get_selected)

    async def _get_states(self, message: dict[str, Any]) -> dict[str, Any]:
        """Get all video stream states."""
        return {
            "type": "video_states",
            "data": self._manager.get_all_states(),
        }

    async def _select_stream(self, message: dict[str, Any]) -> dict[str, Any]:
        """Select a video stream."""
        source = message.get("source", "")
        if not source:
            return {"type": "error", "message": "Source is required"}
        
        success = self._manager.select_stream(source)
        return {
            "type": "video_selected",
            "success": success,
            "source": source if success else None,
            "url": self._manager.get_selected_stream_url() if success else None,
        }

    async def _get_selected(self, message: dict[str, Any]) -> dict[str, Any]:
        """Get currently selected stream."""
        return {
            "type": "video_selected",
            "success": self._manager.get_selected_stream_url() is not None,
            "source": self._manager.get_selected_source(),
            "url": self._manager.get_selected_stream_url(),
        }


class NavigationWebSocketHandler(WebSocketHandler):
    """Handle navigation WebSocket messages."""

    def __init__(self, nav_service: Any) -> None:
        super().__init__("/ws/navigation")
        self._nav_service = nav_service

        self.on("get_status", self._get_status)
        self.on("get_audit_log", self._get_audit_log)

    async def handle_message(self, message: str) -> Optional[dict[str, Any]]:
        """Keep navigation WebSocket read-only; control uses authenticated HTTP."""
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return {"type": "error", "message": "Invalid JSON"}
        if data.get("action") in {
            "authorize", "deauthorize", "send_navigation", "cancel_navigation"
        }:
            return {
                "type": "error",
                "code": "control_over_websocket_disabled",
                "message": "控制操作必须通过经过认证的 HTTP API 执行",
            }
        return await super().handle_message(message)

    async def _authorize(self, message: dict[str, Any]) -> dict[str, Any]:
        """Authorize navigation control."""
        operator = message.get("operator", "web_operator")
        note = message.get("note", "")
        return self._nav_service.authorize(operator, note)

    async def _deauthorize(self, message: dict[str, Any]) -> dict[str, Any]:
        """Deauthorize navigation control."""
        return self._nav_service.deauthorize()

    async def _send_navigation(self, message: dict[str, Any]) -> dict[str, Any]:
        """Send navigation command."""
        pos_x = message.get("pos_x", 0.0)
        pos_y = message.get("pos_y", 0.0)
        pos_z = message.get("pos_z", 0.0)
        angle_yaw = message.get("angle_yaw", 0.0)
        map_id = message.get("map_id", 1)
        return self._nav_service.send_navigation(pos_x, pos_y, pos_z, angle_yaw, map_id)

    async def _cancel_navigation(self, message: dict[str, Any]) -> dict[str, Any]:
        """Cancel navigation task."""
        return self._nav_service.cancel_navigation()

    async def _get_status(self, message: dict[str, Any]) -> dict[str, Any]:
        """Get navigation service status."""
        return self._nav_service.get_status()

    async def _get_audit_log(self, message: dict[str, Any]) -> dict[str, Any]:
        """Get navigation audit log."""
        return {"audit_log": self._nav_service.audit_log}


# Global instances (will be initialized in server.py)
video_ws_handler: Optional[VideoWebSocketHandler] = None
navigation_ws_handler: Optional[NavigationWebSocketHandler] = None


def init_ws_handlers(video_manager: Any, nav_service: Any) -> None:
    """Initialize global WebSocket handlers."""
    global video_ws_handler, navigation_ws_handler
    video_ws_handler = VideoWebSocketHandler(video_manager)
    navigation_ws_handler = NavigationWebSocketHandler(nav_service)
