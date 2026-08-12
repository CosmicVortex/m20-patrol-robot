"""Tests for navigation service with Web authorization."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from backend.app.navigation.service import NavigationService, NavigationAuthorization
from backend.app.navigation.v010 import NavigationSafetySnapshot
from backend.app.robot.basic_client import BasicServerClient


class TestNavigationService:
    """Test NavigationService Web authorization flow."""

    def test_initial_state_not_authorized(self):
        """Service starts without authorization."""
        client = Mock(spec=BasicServerClient)
        safety = NavigationSafetySnapshot(
            control_enabled=True,
            field_authorization="test",
            tcp_connected=True,
            location_normal=True,
            obstacle_avoidance_active=True,
            hard_estop_active=False,
            protective_fault_active=False,
            battery_percent=80,
            active_task=False,
        )
        service = NavigationService(client, safety)
        
        assert service.is_authorized == False
        assert service.get_status()["authorized"] == False

    def test_authorize_via_web(self):
        """Web UI can authorize navigation."""
        client = Mock(spec=BasicServerClient)
        safety = NavigationSafetySnapshot(
            control_enabled=True,
            field_authorization="test",
            tcp_connected=True,
            location_normal=True,
            obstacle_avoidance_active=True,
            hard_estop_active=False,
            protective_fault_active=False,
            battery_percent=80,
            active_task=False,
        )
        service = NavigationService(client, safety)
        
        result = service.authorize("operator1", "Test navigation")
        
        assert result["status"] == "authorized"
        assert service.is_authorized == True
        assert service.get_status()["authorized_by"] == "operator1"
        assert len(service.audit_log) == 1
        assert service.audit_log[0].action == "authorize"

    def test_deauthorize_via_web(self):
        """Web UI can deauthorize navigation."""
        client = Mock(spec=BasicServerClient)
        safety = NavigationSafetySnapshot(
            control_enabled=True,
            field_authorization="test",
            tcp_connected=True,
            location_normal=True,
            obstacle_avoidance_active=True,
            hard_estop_active=False,
            protective_fault_active=False,
            battery_percent=80,
            active_task=False,
        )
        service = NavigationService(client, safety)
        service.authorize("operator1")
        
        result = service.deauthorize()
        
        assert result["status"] == "deauthorized"
        assert service.is_authorized == False

    def test_send_navigation_requires_authorization(self):
        """Send navigation requires prior authorization."""
        client = Mock(spec=BasicServerClient)
        safety = NavigationSafetySnapshot(
            control_enabled=True,
            field_authorization="test",
            tcp_connected=True,
            location_normal=True,
            obstacle_avoidance_active=True,
            hard_estop_active=False,
            protective_fault_active=False,
            battery_percent=80,
            active_task=False,
        )
        service = NavigationService(client, safety)
        
        result = service.send_navigation(1.0, 2.0)
        
        assert result["status"] == "error"
        assert "authorized" in result["message"].lower()

    def test_send_navigation_requires_control_enabled(self):
        """Send navigation requires control_enabled."""
        client = Mock(spec=BasicServerClient)
        safety = NavigationSafetySnapshot(
            control_enabled=False,  # Control disabled
            field_authorization="test",
            tcp_connected=True,
            location_normal=True,
            obstacle_avoidance_active=True,
            hard_estop_active=False,
            protective_fault_active=False,
            battery_percent=80,
            active_task=False,
        )
        service = NavigationService(client, safety)
        service.authorize("operator1")
        
        result = service.send_navigation(1.0, 2.0)
        
        assert result["status"] == "error"
        assert "enabled" in result["message"].lower()

    def test_send_navigation_requires_tcp_connected(self):
        """Send navigation requires TCP connection."""
        client = Mock(spec=BasicServerClient)
        safety = NavigationSafetySnapshot(
            control_enabled=True,
            field_authorization="test",
            tcp_connected=False,  # Not connected
            location_normal=True,
            obstacle_avoidance_active=True,
            hard_estop_active=False,
            protective_fault_active=False,
            battery_percent=80,
            active_task=False,
        )
        service = NavigationService(client, safety)
        service.authorize("operator1")
        
        result = service.send_navigation(1.0, 2.0)
        
        assert result["status"] == "error"
        assert "connected" in result["message"].lower()

    def test_audit_log_tracks_operations(self):
        """Audit log should track all operations."""
        client = Mock(spec=BasicServerClient)
        safety = NavigationSafetySnapshot(
            control_enabled=True,
            field_authorization="test",
            tcp_connected=True,
            location_normal=True,
            obstacle_avoidance_active=True,
            hard_estop_active=False,
            protective_fault_active=False,
            battery_percent=80,
            active_task=False,
        )
        service = NavigationService(client, safety)
        
        # Authorize
        service.authorize("operator1")
        # Try to send (will fail because client is mock)
        with patch.object(client, 'send_control', side_effect=Exception("test")):
            service.send_navigation(1.0, 2.0)
        
        assert len(service.audit_log) >= 2
        assert service.audit_log[0].action == "authorize"
        assert service.audit_log[-1].action == "send"
        assert service.audit_log[-1].success == False

    def test_cancel_navigation_builds_and_sends_cancel_message(self):
        client = Mock(spec=BasicServerClient)
        client.send_control.return_value = Mock()
        safety = NavigationSafetySnapshot(
            control_enabled=True,
            field_authorization="operator1",
            tcp_connected=True,
            location_normal=True,
            obstacle_avoidance_active=True,
            hard_estop_active=False,
            protective_fault_active=False,
            battery_percent=80,
            active_task=True,
        )
        service = NavigationService(client, safety)
        service.authorize("operator1")

        result = service.cancel_navigation()

        assert result["status"] == "cancelled"
        message = client.send_control.call_args.args[0]
        assert (message.message_type, message.command) == (1004, 1)

    def test_cancel_navigation_rejects_when_control_disabled(self):
        client = Mock(spec=BasicServerClient)
        safety = NavigationSafetySnapshot(
            control_enabled=False,
            field_authorization="operator1",
            tcp_connected=True,
            location_normal=True,
            obstacle_avoidance_active=True,
            hard_estop_active=False,
            protective_fault_active=False,
            battery_percent=80,
            active_task=False,
        )
        service = NavigationService(client, safety)
        service.authorize("operator1")

        result = service.cancel_navigation()

        assert result["status"] == "error"
