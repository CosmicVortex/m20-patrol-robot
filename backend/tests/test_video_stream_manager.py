"""Regression tests for video subprocess lifecycle handling."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from backend.app.video.stream_manager import StreamState, VideoStreamManager


def test_default_manager_blocks_real_video_io():
    manager = VideoStreamManager(allow_real_io=False)
    result = asyncio.run(manager.probe_camera("front"))
    assert result["status"] == "BLOCKED"


def test_probe_camera_reports_timeout_without_passing_timeout_to_subprocess_factory():
    manager = VideoStreamManager(allow_real_io=True)
    process = AsyncMock()
    process.terminate = Mock()
    process.kill = Mock()
    process.wait = AsyncMock(side_effect=[asyncio.TimeoutError, None])
    process.returncode = None
    process.communicate = AsyncMock(side_effect=asyncio.TimeoutError)

    with patch(
        "backend.app.video.stream_manager.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=process),
    ) as create_process:
        result = asyncio.run(manager.probe_camera("front"))

    assert result["error"] == "ffprobe timeout (10s)"
    create_process.assert_awaited_once()
    assert "timeout" not in create_process.await_args.kwargs
    process.kill.assert_called_once_with()
    assert process.wait.await_count == 2
    assert manager.get_stream_state("front") is StreamState.ERROR


def test_probe_camera_cleans_up_process_after_probe_exception():
    manager = VideoStreamManager(allow_real_io=True)
    process = AsyncMock()
    process.terminate = Mock()
    process.kill = Mock()
    process.wait = AsyncMock(side_effect=[asyncio.TimeoutError, None])
    process.returncode = None

    with patch(
        "backend.app.video.stream_manager.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=process),
    ):
        process.communicate = AsyncMock(side_effect=RuntimeError("pipe failed"))
        result = asyncio.run(manager.probe_camera("front"))

    assert result["error"] == "Probe error: pipe failed"
    process.kill.assert_called_once_with()
    assert process.wait.await_count == 2


def test_stop_stream_waits_with_asyncio_timeout_and_cleans_up_process():
    manager = VideoStreamManager(allow_real_io=True)
    process = AsyncMock()
    process.returncode = None
    process.terminate = Mock()
    process.kill = Mock()
    process.poll.return_value = None
    process.wait = AsyncMock(return_value=None)
    manager._processes["front"] = process
    manager._stream_states["front"] = StreamState.CONNECTED

    result = asyncio.run(manager.stop_stream("front"))

    assert result == {"status": "stopped", "source": "front"}
    process.terminate.assert_called_once_with()
    process.wait.assert_awaited_once_with()
    assert "front" not in manager._processes
    assert manager.get_stream_state("front") is StreamState.DISCONNECTED


def test_stop_stream_kills_process_when_wait_times_out():
    manager = VideoStreamManager(allow_real_io=True)
    process = AsyncMock()
    process.returncode = None
    process.terminate = Mock()
    process.kill = Mock()
    process.wait = AsyncMock(side_effect=[asyncio.TimeoutError, None])
    manager._processes["front"] = process

    result = asyncio.run(manager.stop_stream("front"))

    assert result["status"] == "stopped"
    process.terminate.assert_called_once_with()
    process.kill.assert_called_once_with()
    assert "front" not in manager._processes
    assert manager.get_stream_state("front") is StreamState.DISCONNECTED


def test_stop_stream_keeps_process_tracked_when_kill_wait_fails():
    manager = VideoStreamManager(allow_real_io=True)
    process = AsyncMock()
    process.returncode = None
    process.terminate = Mock()
    process.kill = Mock()
    process.wait = AsyncMock(side_effect=[asyncio.TimeoutError, asyncio.TimeoutError])
    manager._processes["front"] = process

    result = asyncio.run(manager.stop_stream("front"))

    assert result["status"] == "error"
    assert manager._processes["front"] is process
    assert manager.get_stream_state("front") is StreamState.ERROR


def test_start_stream_restarts_after_process_exits():
    manager = VideoStreamManager(allow_real_io=True)
    process = AsyncMock()
    process.returncode = 1
    process.stdout = None
    process.stderr = None
    process.wait = AsyncMock(return_value=1)
    manager._processes["front"] = process

    with patch(
        "backend.app.video.stream_manager.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=process),
    ) as create_process:
        result = asyncio.run(manager.start_stream("front"))

    assert result["status"] == "started"


def test_manager_rejects_use_from_a_second_event_loop():
    manager = VideoStreamManager(allow_real_io=True)

    async def get_lock():
        async with manager._get_process_lock("front"):
            return "acquired"

    first_loop = asyncio.new_event_loop()
    second_loop = asyncio.new_event_loop()
    try:
        first_loop.run_until_complete(get_lock())
        with pytest.raises(RuntimeError, match="one event loop"):
            second_loop.run_until_complete(get_lock())
    finally:
        first_loop.close()
        second_loop.close()
