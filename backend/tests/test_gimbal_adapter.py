"""Tests for gimbal adapter auto-discovery."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "backend")

from app.gimbal.adapter import SoarGimbalAdapter, GimbalConfig, DiscoveredGimbal


class TestGimbalConfig:
    """Tests for GimbalConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GimbalConfig()
        assert config.host == ""
        assert config.port == 80
        assert config.username == "admin"
        assert config.password == ""  # 默认值为空，要求环境变量设置
        assert config.timeout == 5.0

    def test_custom_config(self):
        """Test custom configuration."""
        config = GimbalConfig(host="10.0.0.1", port=8080, username="test", password="secret")
        assert config.host == "10.0.0.1"
        assert config.port == 8080
        assert config.username == "test"
        assert config.password == "secret"


class TestDiscoveredGimbal:
    """Tests for DiscoveredGimbal dataclass."""

    def test_default_values(self):
        """Test default values for discovered gimbal."""
        gimbal = DiscoveredGimbal(host="10.21.31.108")
        assert gimbal.port == 80
        assert gimbal.model == ""
        assert gimbal.serial == ""
        assert gimbal.accessible is False

    def test_full_values(self):
        """Test full configuration."""
        gimbal = DiscoveredGimbal(
            host="10.21.31.108",
            port=80,
            model="SR-UPA810T609",
            serial="SN123456",
            firmware="v1.2.3",
            rtsp_url="rtsp://10.21.31.108:554/id=1&type=0",
            thermal_rtsp_url="rtsp://10.21.31.108:554/id=2&type=0",
            accessible=True,
        )
        assert gimbal.model == "SR-UPA810T609"
        assert gimbal.serial == "SN123456"
        assert gimbal.accessible is True


class TestGimbalAdapter:
    """Tests for SoarGimbalAdapter core functionality."""

    def test_init_with_config(self):
        """Test adapter initialization with config."""
        config = GimbalConfig(host="10.21.31.108", username="admin", password="pass")
        adapter = SoarGimbalAdapter(config)
        assert adapter.config.host == "10.21.31.108"
        assert adapter._connected is False

    def test_init_without_config(self):
        """Test adapter initialization without config uses defaults."""
        adapter = SoarGimbalAdapter()
        assert adapter.config.host == ""
        assert adapter.config.port == 80

    def test_get_video_urls_default(self):
        """Test video URL generation with defaults."""
        adapter = SoarGimbalAdapter(GimbalConfig(host="10.21.31.108"))
        urls = adapter.get_video_urls()
        assert urls["visible_light"] == "rtsp://10.21.31.108:554/id=1&type=0"
        assert urls["thermal"] == "rtsp://10.21.31.108:554/id=2&type=0"

    def test_get_video_urls_custom(self):
        """Test video URL with custom RTSP URLs."""
        adapter = SoarGimbalAdapter(GimbalConfig(
            host="10.21.31.50",
            rtsp_url="rtsp://custom:554/live",
            thermal_rtsp_url="rtsp://custom:554/thermal"
        ))
        urls = adapter.get_video_urls()
        assert urls["visible_light"] == "rtsp://custom:554/live"
        assert urls["thermal"] == "rtsp://custom:554/thermal"

    def test_ping_host_alive(self):
        """Test host ping when port is open."""
        adapter = SoarGimbalAdapter()

        with patch('socket.socket') as mock_socket:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock

            result = adapter._ping_host("192.168.1.1", 80, timeout=1.0)
            assert result is True

    def test_ping_host_dead(self):
        """Test host ping when port is closed."""
        adapter = SoarGimbalAdapter()

        with patch('socket.socket') as mock_socket:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 111
            mock_socket.return_value = mock_sock

            result = adapter._ping_host("192.168.1.1", 80, timeout=1.0)
            assert result is False

    def test_get_gimbal_info_success(self):
        """Test getting gimbal info from discovered device."""
        adapter = SoarGimbalAdapter(GimbalConfig(host="10.21.31.108"))

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"FlyInfo": {"model": "SR-UPA810T609", "sn": "SN123", "yaw": 0, "pitch": -10}, "CamerInfo": {"zoom": 1}}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_resp):
            info = adapter._get_gimbal_info("10.21.31.108")
            assert info is not None
            assert info.model == "SR-UPA810T609"
            assert info.serial == "SN123"
            assert info.accessible is True

    def test_get_gimbal_info_failure(self):
        """Test getting gimbal info when device not accessible."""
        adapter = SoarGimbalAdapter()

        with patch('urllib.request.urlopen', side_effect=Exception("Connection failed")):
            info = adapter._get_gimbal_info("10.21.31.108")
            assert info is None

    def test_auto_connect_with_configured_host(self):
        """Test auto-connect when host is pre-configured."""
        adapter = SoarGimbalAdapter(GimbalConfig(host="10.21.31.108"))

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"Session": "abc123"}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_resp):
            result = adapter.auto_connect()
            assert result is True
            assert adapter._connected is True

    def test_auto_connect_no_host_fallback_to_scan(self):
        """Test auto-connect without host falls back to scan."""
        adapter = SoarGimbalAdapter()

        mock_info = DiscoveredGimbal(host="10.21.31.108", model="SR-UPA810T609", accessible=True)
        adapter._discovered = [mock_info]

        with patch.object(adapter, '_ping_host', return_value=True):
            with patch.object(adapter, '_get_gimbal_info', return_value=mock_info):
                mock_resp = MagicMock()
                mock_resp.read.return_value = b'{"Session": "abc123"}'
                mock_resp.__enter__ = MagicMock(return_value=mock_resp)
                mock_resp.__exit__ = MagicMock(return_value=False)

                with patch('urllib.request.urlopen', return_value=mock_resp):
                    result = adapter.auto_connect()
                    assert result is True
                    assert adapter.config.host == "10.21.31.108"

    def test_scan_returns_dicts(self):
        """Test scan method returns list of dicts."""
        adapter = SoarGimbalAdapter()

        mock_info = DiscoveredGimbal(host="10.21.31.108", model="SR-UPA810T609", serial="SN123")
        adapter._discovered = [mock_info]

        # Mock discover to avoid actual network scanning
        with patch.object(adapter, 'discover', return_value=[mock_info]):
            result = adapter.scan()
            assert len(result) == 1
            assert result[0]["host"] == "10.21.31.108"
            assert result[0]["model"] == "SR-UPA810T609"
            assert result[0]["serial"] == "SN123"

    def test_discover_empty_result(self):
        """Test discovery with no devices found."""
        adapter = SoarGimbalAdapter()

        with patch.object(adapter, '_ping_host', return_value=False):
            discovered = adapter.discover(ranges=["192.168.255.0/24"], max_hosts=10)
            assert len(discovered) == 0

    def test_close_cleans_up(self):
        """Test close method cleans up connection."""
        adapter = SoarGimbalAdapter(GimbalConfig(host="10.21.31.108"))
        adapter._connected = True
        adapter.close()
        assert adapter._connected is False
        assert adapter._session is None


class TestGimbalHandlers:
    """Tests for gimbal API handlers."""

    def test_handler_imports(self):
        """Test all gimbal handlers can be imported from extended_handlers."""
        from backend.app.api.extended_handlers import (
            GimbalStateHandler,
            GimbalMoveHandler,
            GimbalZoomHandler,
            GimbalAngleHandler,
            GimbalDeviceInfoHandler,
            GimbalVideoHandler,
            GimbalScanHandler,
        )
        assert GimbalStateHandler is not None
        assert GimbalMoveHandler is not None
        assert GimbalZoomHandler is not None
        assert GimbalAngleHandler is not None
        assert GimbalDeviceInfoHandler is not None
        assert GimbalVideoHandler is not None
        assert GimbalScanHandler is not None
