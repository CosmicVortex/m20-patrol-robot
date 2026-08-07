"""Video stream manager for M20 Pro body cameras.

Based on V0.1.0 handbook Appendix 3:
- Front camera: rtsp://10.21.31.103:8554/video1
- Back camera:  rtsp://10.21.31.103:8554/video2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class StreamState(Enum):
    """Camera stream connection state."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class VideoSource(Enum):
    """Video source type."""
    BODY_FRONT = "body_front"
    BODY_BACK = "body_back"
    SUER_SECURITY = "suer_security"  # For future integration


@dataclass
class CameraConfig:
    """Camera configuration from official documentation."""
    source: VideoSource
    name: str
    rtsp_url: str
    protocol: str = "RTSP"
    max_latency_ms: int = 500
    enabled: bool = False


class VideoStreamManager:
    """Manage M20 Pro camera streams."""

    # Official RTSP URLs from V0.1.0 handbook
    DEFAULT_FRONT_CAMERA = "rtsp://10.21.31.103:8554/video1"
    DEFAULT_BACK_CAMERA = "rtsp://10.21.31.103:8554/video2"

    def __init__(self) -> None:
        self._streams: dict[VideoSource, CameraConfig] = {
            VideoSource.BODY_FRONT: CameraConfig(
                source=VideoSource.BODY_FRONT,
                name="Front Camera",
                rtsp_url=self.DEFAULT_FRONT_CAMERA,
            ),
            VideoSource.BODY_BACK: CameraConfig(
                source=VideoSource.BODY_BACK,
                name="Back Camera",
                rtsp_url=self.DEFAULT_BACK_CAMERA,
            ),
        }
        self._stream_states: dict[VideoSource, StreamState] = {
            src: StreamState.DISCONNECTED for src in VideoSource
        }
        self._last_update: dict[VideoSource, Optional[datetime]] = {
            src: None for src in VideoSource
        }
        self._selected_source: Optional[VideoSource] = None

    def get_camera_config(self, source: VideoSource) -> CameraConfig:
        """Get camera configuration."""
        return self._streams[source]

    def get_stream_state(self, source: VideoSource) -> StreamState:
        """Get current stream state."""
        return self._stream_states[source]

    def get_all_states(self) -> dict[str, dict[str, Any]]:
        """Get all stream states for dashboard."""
        return {
            src.value: {
                "state": self._stream_states[src].value,
                "name": self._streams[src].name,
                "rtsp_url": self._streams[src].rtsp_url,
                "enabled": self._streams[src].enabled,
                "last_update": self._last_update[src].isoformat() if self._last_update[src] else None,
                "is_selected": self._selected_source == src,
            }
            for src in VideoSource
        }

    def select_stream(self, source: VideoSource) -> bool:
        """Select which stream to display in Web frontend."""
        if source not in self._streams:
            return False
        self._selected_source = source
        return True

    def get_selected_stream_url(self) -> Optional[str]:
        """Get URL of currently selected stream for Web display."""
        if self._selected_source and self._selected_source in self._streams:
            return self._streams[self._selected_source].rtsp_url
        return None

    def update_stream_state(self, source: VideoSource, state: StreamState) -> None:
        """Update stream connection state."""
        self._stream_states[source] = state
        self._last_update[source] = datetime.now()

    def validate_rtsp_url(self, url: str) -> bool:
        """Validate RTSP URL format."""
        if not url.startswith("rtsp://"):
            return False
        # Basic validation: host:port/path
        parts = url.replace("rtsp://", "").split("/")
        if len(parts) < 1:
            return False
        host_port = parts[0]
        if ":" not in host_port and "." not in host_port:
            return False
        return True


def get_default_video_manager() -> VideoStreamManager:
    """Create default video stream manager."""
    return VideoStreamManager()
