"""Tests for MotionControlService."""

from unittest.mock import MagicMock

import pytest

from backend.app.motion.service import (
    MOTION_STATE_IDLE,
    MOTION_STATE_SOFT_ESTOP,
    GAIT_BASIC_STANDARD,
    MotionControlService,
    MotionSafetySnapshot,
)


class TestMotionControlService:
    """Tests for MotionControlService."""

    def _create_service(self, **kwargs):
        client = MagicMock()
        safety = MotionSafetySnapshot(
            control_enabled=True,
            tcp_connected=True,
            hard_estop_active=False,
            protective_fault_active=False,
            battery_percent=80,
            motion_state=MOTION_STATE_IDLE,
        )
        return MotionControlService(client, safety)

    def test_authorize(self):
        service = self._create_service()
        result = service.authorize("test_user")
        assert result["status"] == "authorized"
        assert service.is_authorized
        assert service.audit_log[-1]["action"] == "authorize"

    def test_deauthorize(self):
        service = self._create_service()
        service.authorize("test_user")
        result = service.deauthorize()
        assert result["status"] == "deauthorized"
        assert not service.is_authorized

    def test_motion_state_switch_success(self):
        service = self._create_service()
        service.authorize("test_user")
        service._client.send_control.return_value = MagicMock()

        result = service.motion_state_switch(MOTION_STATE_SOFT_ESTOP)
        assert result["status"] == "ok"
        service._client.send_control.assert_called_once()

    def test_motion_state_switch_not_authorized(self):
        service = self._create_service()
        result = service.motion_state_switch(MOTION_STATE_IDLE)
        assert result["status"] == "error"

    def test_gait_switch_success(self):
        service = self._create_service()
        service.authorize("test_user")
        service._client.send_control.return_value = MagicMock()

        result = service.gait_switch(GAIT_BASIC_STANDARD)
        assert result["status"] == "ok"

    def test_axis_control_requires_rl_mode(self):
        service = self._create_service()
        service.authorize("test_user")
        # motion_state is IDLE (0), not RL_CONTROL (17)
        result = service.axis_control(0.5, 0.0, 0.0)
        assert result["status"] == "error"
        assert "RL control mode" in result["message"]

    def test_axis_control_invalid_range(self):
        service = self._create_service()
        service.authorize("test_user")
        # Set motion state to RL_CONTROL for this test
        service._safety = MotionSafetySnapshot(
            control_enabled=True,
            tcp_connected=True,
            hard_estop_active=False,
            protective_fault_active=False,
            battery_percent=80,
            motion_state=17,  # RL_CONTROL
        )
        # Test with invalid range
        result = service.axis_control(1.5, 0.0, 0.0)
        assert result["status"] == "error"
        assert "[-1, 1]" in result["message"]

    def test_light_control_success(self):
        service = self._create_service()
        service.authorize("test_user")
        service._client.send_control.return_value = MagicMock()

        result = service.light_control(front=1, back=0)
        assert result["status"] == "ok"

    def test_mode_switch_success(self):
        service = self._create_service()
        service.authorize("test_user")
        service._client.send_control.return_value = MagicMock()

        result = service.mode_switch(1)  # navigation mode
        assert result["status"] == "ok"

    def test_charge_control_success(self):
        service = self._create_service()
        service.authorize("test_user")
        service._client.send_control.return_value = MagicMock()

        result = service.charge_control(1)  # start charge
        assert result["status"] == "ok"

    def test_sleep_mode_success(self):
        service = self._create_service()
        service.authorize("test_user")
        service._client.send_control.return_value = MagicMock()

        result = service.sleep_mode(sleep=True, auto=False, time=10)
        assert result["status"] == "ok"

    def test_sleep_mode_invalid_time(self):
        service = self._create_service()
        service.authorize("test_user")
        result = service.sleep_mode(sleep=True, time=3)  # too low
        assert result["status"] == "error"
        assert "[5, 30]" in result["message"]

    def test_safety_checks_hard_estop(self):
        service = self._create_service()
        service._safety = MotionSafetySnapshot(
            control_enabled=True,
            tcp_connected=True,
            hard_estop_active=True,  # hard estop active
            protective_fault_active=False,
            battery_percent=80,
            motion_state=MOTION_STATE_IDLE,
        )
        service.authorize("test_user")
        result = service.motion_state_switch(MOTION_STATE_IDLE)
        assert result["status"] == "error"

    def test_safety_checks_protective_fault(self):
        service = self._create_service()
        service._safety = MotionSafetySnapshot(
            control_enabled=True,
            tcp_connected=True,
            hard_estop_active=False,
            protective_fault_active=True,
            battery_percent=80,
            motion_state=MOTION_STATE_IDLE,
        )
        service.authorize("test_user")
        result = service.motion_state_switch(MOTION_STATE_IDLE)
        assert result["status"] == "error"

    def test_safety_checks_battery_low(self):
        service = self._create_service()
        service._safety = MotionSafetySnapshot(
            control_enabled=True,
            tcp_connected=True,
            hard_estop_active=False,
            protective_fault_active=False,
            battery_percent=15,  # below 20%
            motion_state=MOTION_STATE_IDLE,
        )
        service.authorize("test_user")
        result = service.motion_state_switch(MOTION_STATE_IDLE)
        assert result["status"] == "error"

    def test_get_status(self):
        service = self._create_service()
        service.authorize("test_user")
        status = service.get_status()
        assert status["authorized"] is True
        assert status["authorized_by"] == "test_user"
        assert status["control_enabled"] is True

    def test_update_safety_from_telemetry(self):
        service = self._create_service()
        telemetry = {
            "basic": {"hes": 1, "motion_state": MOTION_STATE_IDLE},
            "errors": [{"error_code": 0x8002}],
            "battery_percent": 75,
            "tcp_connected": True,
        }
        service.update_safety(telemetry)
        assert service._safety.hard_estop_active is True
        assert service._safety.protective_fault_active is True
        assert service._safety.battery_percent == 75

    def test_protective_fault_detection(self):
        errors = [
            {"error_code": 0x8002},  # motor overtemp protection
            {"error_code": 0x8008},  # driver undervoltage
            {"error_code": 0x8103},  # battery protection
        ]
        assert MotionControlService._detect_protective_fault(errors) is True

        errors = [
            {"error_code": 0x8001},  # motor overtemp warning (not protection)
            {"error_code": 0x8102},  # low battery warning
        ]
        assert MotionControlService._detect_protective_fault(errors) is False
