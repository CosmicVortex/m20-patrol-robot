"""Video stream proxy for M20 Pro body cameras.

Connects to AOS RTSP streams and serves them via WebSocket to the web frontend.
Supports H.264/H.265 transcoding via FFmpeg.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class StreamState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class CameraConfig:
    source: str
    name: str
    rtsp_url: str
    enabled: bool = False


class VideoStreamManager:
    """Manage M20 Pro camera RTSP streams."""

    # Official RTSP URLs from V1.2.1 Appendix 3
    DEFAULT_FRONT_CAMERA = "rtsp://10.21.31.103:8554/video1"
    DEFAULT_BACK_CAMERA = "rtsp://10.21.31.103:8554/video2"

    def __init__(self) -> None:
        self._streams: dict[str, CameraConfig] = {
            "front": CameraConfig(
                source="front",
                name="前向本体相机",
                rtsp_url=self.DEFAULT_FRONT_CAMERA,
            ),
            "rear": CameraConfig(
                source="rear",
                name="后向本体相机",
                rtsp_url=self.DEFAULT_BACK_CAMERA,
            ),
        }
        self._stream_states: dict[str, StreamState] = {
            src: StreamState.DISCONNECTED for src in self._streams
        }
        self._last_update: dict[str, Optional[datetime]] = {
            src: None for src in self._streams
        }
        self._processes: dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()

    def get_camera_config(self, source: str) -> Optional[CameraConfig]:
        """Get camera configuration."""
        return self._streams.get(source)

    def get_stream_state(self, source: str) -> StreamState:
        """Get current stream state."""
        return self._stream_states.get(source, StreamState.DISCONNECTED)

    def get_all_states(self) -> dict[str, dict[str, Any]]:
        """Get all stream states for dashboard."""
        return {
            source: {
                "state": state.value,
                "last_update": self._last_update[source].isoformat() if self._last_update[source] else None,
                "rtsp_url": self._streams[source].rtsp_url,
            }
            for source, state in self._stream_states.items()
        }

    async def probe_camera(self, source: str) -> dict[str, Any]:
        """Probe camera to check RTSP accessibility and encode format."""
        config = self._streams.get(source)
        if not config:
            return {"error": f"Unknown camera source: {source}"}

        result = {
            "source": source,
            "rtsp_url": config.rtsp_url,
            "accessible": False,
            "codec": None,
            "resolution": None,
            "fps": None,
            "error": None,
        }

        try:
            # Use ffprobe to check stream
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "stream=codec_name,width,height,r_frame_rate",
                "-of", "json",
                config.rtsp_url,
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                timeout=10,
            )
            
            try:
                stdout, stderr = await proc.communicate()
                
                if proc.returncode == 0:
                    import json
                    data = json.loads(stdout)
                    streams = data.get("streams", [])
                    
                    if streams:
                        stream = streams[0]
                        result["accessible"] = True
                        result["codec"] = stream.get("codec_name")
                        result["resolution"] = f"{stream.get('width')}x{stream.get('height')}"
                        
                        # Parse fps
                        fps = stream.get("r_frame_rate", "0/1")
                        if "/" in fps:
                            num, den = fps.split("/")
                            result["fps"] = float(num) / float(den) if float(den) > 0 else 0
                        else:
                            result["fps"] = float(fps) if fps else 0
                    else:
                        result["error"] = "No video stream found"
                else:
                    result["error"] = f"ffprobe failed: {stderr.decode()[:200]}"
                    
            except asyncio.TimeoutError:
                result["error"] = "ffprobe timeout (10s)"
            except Exception as e:
                result["error"] = f"Probe error: {str(e)}"
                
        except FileNotFoundError:
            result["error"] = "ffprobe not installed"
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"

        # Update state
        with self._lock:
            if result["accessible"]:
                self._stream_states[source] = StreamState.CONNECTED
            else:
                self._stream_states[source] = StreamState.ERROR
            self._last_update[source] = datetime.utcnow()

        return result

    async def start_stream(self, source: str) -> dict[str, Any]:
        """Start RTSP stream with FFmpeg transcode."""
        config = self._streams.get(source)
        if not config:
            return {"error": f"Unknown camera source: {source}"}

        # Check if already running
        if source in self._processes:
            proc = self._processes[source]
            if proc.poll() is None:
                return {"status": "already_running", "source": source}

        with self._lock:
            self._stream_states[source] = StreamState.CONNECTING

        # FFmpeg command to transcode RTSP to HLS or raw H.264
        # Using raw H.264 for low latency, can be played in video element
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "warning",
            "-i", config.rtsp_url,
            "-c:v", "copy",  # Copy video stream (no re-encode)
            "-an",  # No audio
            "-f", "h264",  # Raw H.264 output
            "pipe:1",  # Output to stdout
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            self._processes[source] = proc
            self._stream_states[source] = StreamState.CONNECTED
            self._last_update[source] = datetime.utcnow()

            logger.info(f"Started RTSP stream for {source}: {config.rtsp_url}")
            return {"status": "started", "source": source, "rtsp_url": config.rtsp_url}

        except Exception as e:
            self._stream_states[source] = StreamState.ERROR
            logger.error(f"Failed to start stream for {source}: {e}")
            return {"error": str(e)}

    async def stop_stream(self, source: str) -> dict[str, Any]:
        """Stop RTSP stream."""
        proc = self._processes.get(source)
        if proc:
            try:
                proc.terminate()
                await proc.wait(timeout=5)
                del self._processes[source]
                
                with self._lock:
                    self._stream_states[source] = StreamState.DISCONNECTED
                    self._last_update[source] = datetime.utcnow()
                
                logger.info(f"Stopped RTSP stream for {source}")
                return {"status": "stopped", "source": source}
            except Exception as e:
                logger.error(f"Error stopping stream {source}: {e}")
                return {"error": str(e)}

        return {"status": "not_running", "source": source}

    def cleanup(self) -> None:
        """Stop all streams and cleanup."""
        for source in list(self._processes.keys()):
            asyncio.create_task(self.stop_stream(source))
