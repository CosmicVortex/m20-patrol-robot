"""运动控制服务测试。

覆盖所有官方文档定义的控制命令和安全管理逻辑。
"""

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
    """运动控制服务测试。"""

    def _create_service(self, **kwargs):
        """创建测试服务实例。"""
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
        """授权测试。"""
        service = self._create_service()
        result = service.authorize("test_user")
        assert result["status"] == "authorized"
        assert service.is_authorized

    def test_deauthorize(self):
        """撤销授权测试。"""
        service = self._create_service()
        service.authorize("test_user")
        result = service.deauthorize()
        assert result["status"] == "deauthorized"
        assert not service.is_authorized

    def test_motion_state_switch_success(self):
        """运动状态切换成功测试。"""
        service = self._create_service()
        service.authorize("test_user")
        service._client.send_control.return_value = MagicMock()

        result = service.motion_state_switch(MOTION_STATE_SOFT_ESTOP)
        assert result["status"] == "ok"
        service._client.send_control.assert_called_once()

    def test_motion_state_switch_not_authorized(self):
        """未授权状态切换拒绝测试。"""
        service = self._create_service()
        result = service.motion_state_switch(MOTION_STATE_IDLE)
        assert result["status"] == "error"

    def test_gait_switch_success(self):
        """步态切换成功测试。"""
        service = self._create_service()
        service.authorize("test_user")
        service._client.send_control.return_value = MagicMock()

        result = service.gait_switch(GAIT_BASIC_STANDARD)
        assert result["status"] == "ok"

    def test_axis_control_requires_rl_mode(self):
        """轴控制需要RL模式测试。"""
        service = self._create_service()
        service.authorize("test_user")
        result = service.axis_control(0.5, 0.0, 0.0)
        assert result["status"] == "error"
        assert "RL control mode" in result["message"]

    def test_axis_control_invalid_range(self):
        """轴控制范围验证测试。"""
        service = self._create_service()
        service.authorize("test_user")
        # 设置RL控制模式
        service._safety = MotionSafetySnapshot(
            control_enabled=True,
            tcp_connected=True,
            hard_estop_active=False,
            protective_fault_active=False,
            battery_percent=80,
            motion_state=17,  # RL_CONTROL
        )
        result = service.axis_control(1.5, 0.0, 0.0)
        assert result["status"] == "error"
        assert "[-1, 1]" in result["message"]

    def test_light_control_success(self):
        """照明灯控制成功测试。"""
        service = self._create_service()
        service.authorize("test_user")
        service._client.send_control.return_value = MagicMock()

        result = service.light_control(front=1, back=0)
        assert result["status"] == "ok"

    def test_mode_switch_success(self):
        """模式切换成功测试。"""
        service = self._create_service()
        service.authorize("test_user")
        service._client.send_control.return_value = MagicMock()

        result = service.mode_switch(1)  # 导航模式
        assert result["status"] == "ok"

    def test_charge_control_success(self):
        """充电控制成功测试。"""
        service = self._create_service()
        service.authorize("test_user")
        service._client.send_control.return_value = MagicMock()

        result = service.charge_control(1)  # 开始充电
        assert result["status"] == "ok"

    def test_sleep_mode_success(self):
        """休眠模式设置成功测试。"""
        service = self._create_service()
        service.authorize("test_user")
        service._client.send_control.return_value = MagicMock()

        result = service.sleep_mode(sleep=True, auto=False, time=10)
        assert result["status"] == "ok"

    def test_sleep_mode_invalid_time(self):
        """休眠时间参数验证测试。"""
        service = self._create_service()
        service.authorize("test_user")
        result = service.sleep_mode(sleep=True, time=3)  # 太低
        assert result["status"] == "error"
        assert "[5, 30]" in result["message"]

    def test_safety_checks_hard_estop(self):
        """硬急停安全检查测试。"""
        service = self._create_service()
        service._safety = MotionSafetySnapshot(
            control_enabled=True,
            tcp_connected=True,
            hard_estop_active=True,
            protective_fault_active=False,
            battery_percent=80,
            motion_state=MOTION_STATE_IDLE,
        )
        service.authorize("test_user")
        result = service.motion_state_switch(MOTION_STATE_IDLE)
        assert result["status"] == "error"

    def test_safety_checks_protective_fault(self):
        """保护故障安全检查测试。"""
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
        """低电量安全检查测试。"""
        service = self._create_service()
        service._safety = MotionSafetySnapshot(
            control_enabled=True,
            tcp_connected=True,
            hard_estop_active=False,
            protective_fault_active=False,
            battery_percent=15,
            motion_state=MOTION_STATE_IDLE,
        )
        service.authorize("test_user")
        result = service.motion_state_switch(MOTION_STATE_IDLE)
        assert result["status"] == "error"

    def test_get_status(self):
        """状态查询测试。"""
        service = self._create_service()
        service.authorize("test_user")
        status = service.get_status()
        assert status["authorized"] is True
        assert status["authorized_by"] == "test_user"
        assert status["control_enabled"] is True

    def test_update_safety_from_telemetry(self):
        """遥测数据同步测试。"""
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
        """保护故障检测测试。"""
        errors = [
            {"error_code": 0x8002},  # 电机过温保护
            {"error_code": 0x8008},  # 驱动器欠压
        ]
        assert MotionControlService._detect_protective_fault(errors) is True

        errors = [
            {"error_code": 0x8001},  # 电机过温预警（非保护）
            {"error_code": 0x8102},  # 低电量预警
        ]
        assert MotionControlService._detect_protective_fault(errors) is False
