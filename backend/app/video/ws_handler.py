"""Video stream WebSocket handler for Web frontend."""

from __future__ import annotations

import asyncio
from typing import Any

from backend.app.video.video_manager import VideoStreamManager


class VideoWebSocketHandler:
    """Handle video stream WebSocket connections."""

    def __init__(self, manager: VideoStreamManager) -> None:
        self._manager = manager
        self._subscriptions: list[Any] = []

    async def handle_video_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Handle video-related WebSocket messages."""
        action = message.get("action")
        source = message.get("source")

        if action == "get_states":
            return {"type": "video_states", "data": self._manager.get_all_states()}

        if action == "select_stream" and source:
            success = self._manager.select_stream(source)
            return {
                "type": "video_selected",
                "success": success,
                "url": self._manager.get_selected_stream_url() if success else None,
            }

        if action == "get_selected":
            return {
                "type": "video_selected",
                "url": self._manager.get_selected_stream_url(),
            }

        return {"type": "error", "message": "Unknown video action"}

    def get_state_update(self) -> dict[str, Any]:
        """Get current video states for push updates."""
        return {
            "type": "video_states",
            "data": self._manager.get_all_states(),
        }
