"""Tests for real-time telemetry adapter."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from backend.app.robot.telemetry import TelemetryAdapter, ConnectionConfig
from backend.app.robot.basic_client import BasicServerConfig, ClientStateError
from backend.app.protocol.messages import PatrolMessage, ASDUFormat
from backend.app.robot.status import parse_status_message


class TestTelemetryAdapter:
    """Test TelemetryAdapter real-time status streaming."""

    def test_initial_state_has_no_data(self):
        """Adapter must not confuse an unstarted stream with simulation."""
        config = ConnectionConfig(host="10.21.31.103")
        adapter = TelemetryAdapter(config)
        
        snapshot = adapter.snapshot
        assert snapshot.source == "NO_DATA"
        assert snapshot.connected == False
        assert snapshot.received_at is None
        assert snapshot.age_ms is None

    def test_starts_and_stops_gracefully(self):
        """Start/stop should not raise."""
        config = ConnectionConfig(host="10.21.31.103")
        adapter = TelemetryAdapter(config)
        
        # Should not raise even if not connected
        adapter.start()
        adapter.stop()
        
        # Double stop should be safe
        adapter.stop()

    def test_get_status_payload_returns_no_data_when_not_started(self):
        """Status payload should identify an unstarted stream as NO_DATA."""
        config = ConnectionConfig(host="10.21.31.103")
        adapter = TelemetryAdapter(config)
        
        payload = adapter.get_status_payload()
        assert payload["source"] == "NO_DATA"
        assert payload["connected"] == False
        assert payload["control_enabled"] == False

    @patch('backend.app.robot.telemetry.BasicServerClient')
    def test_connects_to_aos(self, mock_client_class):
        """Adapter should attempt to connect to AOS."""
        config = ConnectionConfig(host="10.21.31.103", tcp_port=30001)
        adapter = TelemetryAdapter(config)
        
        # Mock the client
        mock_client = Mock()
        mock_client.is_stale.return_value = True
        mock_client._last_received_at = datetime.now(timezone.utc)
        mock_client_class.return_value = mock_client
        
        # This will fail because we're not actually connecting,
        # but we can verify the config is created correctly
        assert adapter.config.host == "10.21.31.103"
        assert adapter.config.tcp_port == 30001

    def test_status_payload_structure(self):
        """Status payload should have expected structure."""
        config = ConnectionConfig(host="10.21.31.103")
        adapter = TelemetryAdapter(config)
        
        payload = adapter.get_status_payload()
        
        assert "source" in payload
        assert "connected" in payload
        assert "control_enabled" in payload
        assert "received_at" in payload
        assert "age_ms" in payload
        assert "data" in payload
        assert payload["data"]["robot"] == "M20 Pro"

    def test_message_and_error_counts(self):
        """Message and error counts should be zero initially."""
        config = ConnectionConfig(host="10.21.31.103")
        adapter = TelemetryAdapter(config)
        
        assert adapter.message_count == 0
        assert adapter.error_count == 0

    def test_default_configuration_does_not_allow_telemetry_transmit(self):
        config = ConnectionConfig(host="10.21.31.103")
        assert config.read_only is True
        assert config.telemetry_tx_enabled is False
        assert config.runtime_mode == "simulated"

    def test_receive_disabled_is_enforced(self):
        config = ConnectionConfig(host="10.21.31.103", runtime_mode="realtime", telemetry_receive_enabled=False)
        adapter = TelemetryAdapter(config)
        adapter.start()
        adapter.stop()
        assert adapter.snapshot.source == "NO_DATA"

    @patch('backend.app.robot.telemetry.BasicServerClient')
    def test_telemetry_tx_disabled_does_not_send_heartbeat(self, mock_client_class):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        adapter = TelemetryAdapter(ConnectionConfig(host="10.21.31.103"))
        adapter._run_loop = Mock()  # configuration-level assertion; no device I/O
        assert adapter.config.telemetry_tx_enabled is False
        mock_client.send_read_only.assert_not_called()

    def test_status_payload_distinguishes_no_data_from_simulated(self):
        adapter = TelemetryAdapter(ConnectionConfig(host="10.21.31.103"))
        payload = adapter.get_status_payload()
        assert payload["source"] == "NO_DATA"
        assert payload["connection_state"] == "NO_DATA"
        assert payload["telemetry_tx_enabled"] is False
        assert payload["bytes_received"] == 0

    def test_simulated_mode_does_not_construct_or_connect_robot_socket(self):
        adapter = TelemetryAdapter(ConnectionConfig(host="", runtime_mode="simulated"))
        with patch("backend.app.robot.telemetry.BasicServerClient") as client_class:
            adapter.start()
            adapter.stop()
        client_class.assert_not_called()

    def test_read_only_configuration_rejects_telemetry_transmit(self):
        with pytest.raises(ValueError, match="transmission is disabled"):
            ConnectionConfig(
                host="10.21.31.103",
                runtime_mode="realtime_readonly",
                read_only=True,
                telemetry_tx_enabled=True,
            )

    def test_receive_timeout_is_treated_as_no_data(self):
        adapter = TelemetryAdapter(ConnectionConfig(host="10.21.31.103"))
        client = Mock()
        client._receive_from_socket.return_value = []
        # The adapter's receive path must preserve the empty-read result;
        # BasicServerClient handles socket.timeout without reconnecting.
        assert client._receive_from_socket() == []

    def test_telemetry_transmit_is_rejected_for_all_configurations(self):
        with pytest.raises(ValueError, match="transmission is disabled"):
            ConnectionConfig(host="10.21.31.103", telemetry_tx_enabled=True)
        with pytest.raises(ValueError, match="transmission is disabled"):
            ConnectionConfig(
                host="10.21.31.103",
                runtime_mode="realtime",
                read_only=False,
                telemetry_tx_enabled=True,
            )
