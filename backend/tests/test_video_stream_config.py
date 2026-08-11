"""Test for video stream manager RTSP URL configuration."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.video.stream_manager import VideoStreamManager


def test_stream_manager_has_documented_rtsp_defaults():
    """Test that default RTSP URLs match official documentation."""
    mgr = VideoStreamManager(allow_real_io=False)

    # Verify documented RTSP URLs for body cameras (V1.2.1 appendix)
    front_config = mgr.get_camera_config("front")
    assert front_config is not None
    assert front_config.rtsp_url == "rtsp://10.21.31.103:8554/video1"

    rear_config = mgr.get_camera_config("rear")
    assert rear_config is not None
    assert rear_config.rtsp_url == "rtsp://10.21.31.103:8554/video2"

    # Thermal camera RTSP comes from gimbal, not hardcoded
    thermal_config = mgr.get_camera_config("thermal")
    assert thermal_config is not None
    assert thermal_config.rtsp_url == ""  # To be configured from gimbal


def test_stream_manager_can_override_rtsp():
    """Test that RTSP URLs can be configured for different sites."""
    mgr = VideoStreamManager(allow_real_io=False)

    # Override RTSP URL for different deployment
    assert mgr.set_rtsp_url("front", "rtsp://192.168.1.100:8554/video1")
    config = mgr.get_camera_config("front")
    assert config.rtsp_url == "rtsp://192.168.1.100:8554/video1"


def test_thermal_rtsp_from_gimbal():
    """Test that thermal camera RTSP is configured from gimbal."""
    mgr = VideoStreamManager(allow_real_io=False)

    # Configure thermal RTSP from gimbal (as per documentation)
    gimbal_host = "192.168.1.108"
    thermal_rtsp = f"rtsp://{gimbal_host}:554/id=2&type=0"
    assert mgr.set_rtsp_url("thermal", thermal_rtsp)

    config = mgr.get_camera_config("thermal")
    assert config.rtsp_url == thermal_rtsp
