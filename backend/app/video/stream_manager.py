"""Video stream proxy for M20 Pro body cameras.

Connects to AOS RTSP streams and serves them via WebSocket to the web frontend.
Supports H.264/H.265 transcoding via FFmpeg.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)
UTC = timezone.utc


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
    """Manage M20 Pro camera RTSP streams and subprocess lifecycles."""

    DEFAULT_FRONT_CAMERA = ""
    DEFAULT_BACK_CAMERA = ""
    PROCESS_WAIT_TIMEOUT_S = 5
    PROBE_TIMEOUT_S = 10

    def __init__(self, *, allow_real_io: bool = False) -> None:
        if type(allow_real_io) is not bool:
            raise ValueError("allow_real_io must be boolean")
        self.allow_real_io = allow_real_io
        self._streams: Dict[str, CameraConfig] = {
            "front": CameraConfig("front", "前向本体相机", self.DEFAULT_FRONT_CAMERA),
            "rear": CameraConfig("rear", "后向本体相机", self.DEFAULT_BACK_CAMERA),
        }
        self._stream_states: Dict[str, StreamState] = {
            source: StreamState.DISCONNECTED for source in self._streams
        }
        self._last_update: Dict[str, Optional[datetime]] = {
            source: None for source in self._streams
        }
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        # Create locks lazily inside one owning event loop. Python 3.8 binds
        # Lock construction to the current loop; manager state is shared, so
        # silently creating one lock per loop would not preserve mutual exclusion.
        self._owner_loop: Optional[asyncio.AbstractEventLoop] = None
        self._process_locks: Dict[str, Optional[asyncio.Lock]] = {
            source: None for source in self._streams
        }
        self._watchers: Dict[str, asyncio.Task] = {}
        self._drainers: Dict[str, Set[asyncio.Task]] = {
            source: set() for source in self._streams
        }
        self._selected_source: Optional[str] = None
        self._lock = threading.Lock()

    def _get_process_lock(self, source: str) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        if self._owner_loop is None:
            self._owner_loop = loop
        elif self._owner_loop is not loop:
            raise RuntimeError("VideoStreamManager must be used by one event loop")
        lock = self._process_locks[source]
        if lock is None:
            lock = asyncio.Lock()
            self._process_locks[source] = lock
        return lock

    def get_camera_config(self, source: str) -> Optional[CameraConfig]:
        return self._streams.get(source)

    def get_stream_state(self, source: str) -> StreamState:
        return self._stream_states.get(source, StreamState.DISCONNECTED)

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        return {
            source: {
                "state": state.value,
                "last_update": self._last_update[source].isoformat()
                if self._last_update[source]
                else None,
                "rtsp_url": self._streams[source].rtsp_url,
            }
            for source, state in self._stream_states.items()
        }

    def select_stream(self, source: str) -> bool:
        if source not in self._streams:
            return False
        self._selected_source = source
        return True

    def get_selected_source(self) -> Optional[str]:
        return self._selected_source

    def get_selected_stream_url(self) -> Optional[str]:
        if self._selected_source is None:
            return None
        config = self._streams.get(self._selected_source)
        return config.rtsp_url if config else None

    async def probe_camera(self, source: str) -> Dict[str, Any]:
        """Probe RTSP accessibility and codec metadata without leaking ffprobe."""
        if source not in self._streams:
            return {"error": f"Unknown camera source: {source}"}
        self._get_process_lock(source)
        if not self.allow_real_io:
            return {"error": "real video I/O is disabled by default", "status": "BLOCKED"}
        config = self._streams[source]
        result: Dict[str, Any] = {
            "source": source,
            "rtsp_url": config.rtsp_url,
            "accessible": False,
            "codec": None,
            "resolution": None,
            "fps": None,
            "error": None,
        }
        proc: Optional[asyncio.subprocess.Process] = None
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffprobe",
                "-v", "error",
                "-show_entries", "stream=codec_name,width,height,r_frame_rate",
                "-of", "json",
                config.rtsp_url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self.PROBE_TIMEOUT_S
                )
                if proc.returncode == 0:
                    data = json.loads(stdout)
                    streams = data.get("streams", [])
                    if streams:
                        stream = streams[0]
                        result["accessible"] = True
                        result["codec"] = stream.get("codec_name")
                        result["resolution"] = f"{stream.get('width')}x{stream.get('height')}"
                        fps = stream.get("r_frame_rate", "0/1")
                        if "/" in fps:
                            numerator, denominator = fps.split("/", 1)
                            result["fps"] = (
                                float(numerator) / float(denominator)
                                if float(denominator) > 0
                                else 0
                            )
                        else:
                            result["fps"] = float(fps) if fps else 0
                    else:
                        result["error"] = "No video stream found"
                else:
                    result["error"] = f"ffprobe failed: {stderr.decode(errors='replace')[:200]}"
            except asyncio.TimeoutError:
                result["error"] = f"ffprobe timeout ({self.PROBE_TIMEOUT_S}s)"
            except Exception as error:
                result["error"] = f"Probe error: {error}"
        except FileNotFoundError:
            result["error"] = "ffprobe not installed"
        except Exception as error:
            result["error"] = f"Unexpected error: {error}"
        finally:
            if proc is not None and proc.returncode is None:
                await self._terminate_process(proc, "ffprobe")

        with self._lock:
            self._stream_states[source] = (
                StreamState.CONNECTED if result["accessible"] else StreamState.ERROR
            )
            self._last_update[source] = datetime.now(UTC)
        return result

    async def start_stream(self, source: str) -> Dict[str, Any]:
        """Start an FFmpeg stream and monitor all owned subprocess resources."""
        if not self.allow_real_io:
            return {"error": "real video I/O is disabled by default", "status": "BLOCKED"}
        config = self._streams.get(source)
        if not config:
            return {"error": f"Unknown camera source: {source}"}

        async with self._get_process_lock(source):
            existing = self._processes.get(source)
            if existing is not None and existing.returncode is None:
                return {"status": "already_running", "source": source}
            stale = self._processes.get(source)
            if stale is not None:
                stopped = await self._terminate_process(stale, f"stale stream {source}")
                if not stopped:
                    with self._lock:
                        self._stream_states[source] = StreamState.ERROR
                    return {"status": "error", "message": "stale process did not exit"}
                self._processes.pop(source, None)
                await self._cancel_tasks(source)
            with self._lock:
                self._stream_states[source] = StreamState.CONNECTING

            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "warning",
                "-i", config.rtsp_url,
                "-c:v", "copy", "-an", "-f", "h264", "pipe:1",
            ]
            proc: Optional[asyncio.subprocess.Process] = None
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                self._processes[source] = proc
                with self._lock:
                    self._stream_states[source] = StreamState.CONNECTED
                    self._last_update[source] = datetime.now(UTC)
                watcher = asyncio.create_task(self._watch_process(source, proc))
                self._watchers[source] = watcher
                watcher.add_done_callback(
                    lambda task, stream=source: self._watcher_done(stream, task)
                )
                self._start_drainers(source, proc)
                logger.info("Started RTSP stream for %s: %s", source, config.rtsp_url)
                return {"status": "started", "source": source, "rtsp_url": config.rtsp_url}
            except BaseException as error:
                if proc is not None:
                    await self._terminate_process(proc, f"failed stream {source}")
                    self._processes.pop(source, None)
                    await self._cancel_tasks(source)
                with self._lock:
                    self._stream_states[source] = StreamState.ERROR
                logger.error("Failed to start stream for %s: %s", source, error)
                if isinstance(error, asyncio.CancelledError):
                    raise
                return {"error": str(error)}

    async def stop_stream(self, source: str) -> Dict[str, Any]:
        """Stop a stream, retaining failed process references for retry/diagnosis."""
        if source not in self._streams:
            return {"error": f"Unknown camera source: {source}"}
        async with self._get_process_lock(source):
            proc = self._processes.get(source)
            if proc is None:
                return {"status": "not_running", "source": source}
            try:
                stopped = await self._finalize_stop(source, proc)
                if not stopped:
                    return {"status": "error", "message": "process did not exit"}
                logger.info("Stopped RTSP stream for %s", source)
                return {"status": "stopped", "source": source}
            except asyncio.CancelledError:
                await asyncio.shield(self._finalize_stop(source, proc))
                raise
            except Exception as error:
                with self._lock:
                    self._stream_states[source] = StreamState.ERROR
                logger.error("Error stopping stream %s: %s", source, error)
                return {"status": "error", "message": str(error)}

    async def _terminate_process(self, proc: asyncio.subprocess.Process, label: str) -> bool:
        if proc.returncode is not None:
            return True
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=self.PROCESS_WAIT_TIMEOUT_S)
            return True
        except asyncio.TimeoutError:
            proc.kill()
            try:
                await asyncio.wait_for(proc.wait(), timeout=self.PROCESS_WAIT_TIMEOUT_S)
                return True
            except ProcessLookupError:
                return True
            except Exception as error:
                logger.error("%s process did not exit after kill: %s", label, error)
                return False
        except ProcessLookupError:
            return True
        except Exception as error:
            logger.error("%s process termination failed: %s", label, error)
            return False

    def _start_drainers(self, source: str, proc: asyncio.subprocess.Process) -> None:
        for pipe in (proc.stdout, proc.stderr):
            if pipe is not None:
                task = asyncio.create_task(self._drain_pipe(pipe))
                self._drainers[source].add(task)
                task.add_done_callback(
                    lambda completed, stream=source: self._drainer_done(stream, completed)
                )

    async def _drain_pipe(self, pipe: Any) -> None:
        try:
            while await pipe.read(65536):
                pass
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.warning("Video subprocess pipe drain failed: %s", error)

    async def _watch_process(self, source: str, proc: asyncio.subprocess.Process) -> None:
        try:
            return_code = await proc.wait()
            if self._processes.get(source) is proc:
                self._processes.pop(source, None)
                with self._lock:
                    self._stream_states[source] = (
                        StreamState.DISCONNECTED if return_code == 0 else StreamState.ERROR
                    )
                    self._last_update[source] = datetime.now(UTC)
        except asyncio.CancelledError:
            raise
        finally:
            if self._watchers.get(source) is asyncio.current_task():
                self._watchers.pop(source, None)

    def _watcher_done(self, source: str, task: asyncio.Task[None]) -> None:
        if not task.cancelled() and (error := task.exception()) is not None:
            logger.error("Video watcher failed for %s: %s", source, error)

    def _drainer_done(self, source: str, task: asyncio.Task[None]) -> None:
        self._drainers[source].discard(task)
        if not task.cancelled() and (error := task.exception()) is not None:
            logger.warning("Video drainer failed for %s: %s", source, error)

    async def _cancel_tasks(
        self, source: str, exclude: Optional[asyncio.Task] = None
    ) -> None:
        watcher = self._watchers.pop(source, None)
        if watcher is not None and watcher is not exclude:
            watcher.cancel()
        tasks: List[asyncio.Task] = []
        if watcher is not None and watcher is not exclude:
            tasks.append(watcher)
        for task in list(self._drainers[source]):
            if task is not exclude:
                task.cancel()
                tasks.append(task)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._drainers[source].difference_update(tasks)

    async def _finalize_stop(
        self, source: str, proc: asyncio.subprocess.Process
    ) -> bool:
        stopped = await self._terminate_process(proc, f"stream {source}")
        if stopped:
            self._processes.pop(source, None)
            await self._cancel_tasks(source, exclude=asyncio.current_task())
            with self._lock:
                self._stream_states[source] = StreamState.DISCONNECTED
                self._last_update[source] = datetime.now(UTC)
        else:
            with self._lock:
                self._stream_states[source] = StreamState.ERROR
        return stopped

    async def cleanup(self) -> None:
        """Stop all streams and await cleanup completion."""
        if self._owner_loop is not None:
            current_loop = asyncio.get_running_loop()
            if current_loop is not self._owner_loop:
                raise RuntimeError("VideoStreamManager must be used by one event loop")
        sources = set(self._processes) | set(self._watchers) | {
            source for source, tasks in self._drainers.items() if tasks
        }
        for source in sources:
            if source in self._processes:
                await self.stop_stream(source)
            else:
                await self._cancel_tasks(source)
