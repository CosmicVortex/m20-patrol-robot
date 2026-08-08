"""Video stream WebSocket handler for Web frontend."""

from __future__ import annotations

from typing import Any

from backend.app.video.stream_manager import VideoStreamManager


class VideoWebSocketHandler:
    """Handle video stream WebSocket connections."""

    def __init__(self, manager: VideoStreamManager) -> None:
        self._manager = manager


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
                "source": source if success else None,
                "url": self._manager.get_selected_stream_url() if success else None,
            }

        if action == "select_stream":
            return {
                "type": "video_selected",
                "success": False,
                "source": None,
                "url": None,
            }

        if action == "get_selected":
            return {
                "type": "video_selected",
                "success": self._manager.get_selected_stream_url() is not None,
                "source": self._manager.get_selected_source(),
                "url": self._manager.get_selected_stream_url(),
            }

        return {"type": "error", "message": "Unknown video action"}

    def get_state_update(self) -> dict[str, Any]:
        """Get current video states for push updates."""
        return {
            "type": "video_states",
            "data": self._manager.get_all_states(),
        }
