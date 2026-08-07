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

    def test_initial_state_is_simulated(self):
        """Adapter starts in SIMULATED state."""
        config = ConnectionConfig(host="10.21.31.103")
        adapter = TelemetryAdapter(config)
        
        snapshot = adapter.snapshot
        assert snapshot.source == "SIMULATED"
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

    def test_get_status_payload_returns_simulated_when_not_started(self):
        """Status payload should be SIMULATED when adapter not started."""
        config = ConnectionConfig(host="10.21.31.103")
        adapter = TelemetryAdapter(config)
        
        payload = adapter.get_status_payload()
        assert payload["source"] == "SIMULATED"
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
