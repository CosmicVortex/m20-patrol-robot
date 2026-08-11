"""Motion control service for M20 Pro robot.

Implements basic motion commands per V1.2.1 §1.2.2-1.2.8:
- Motion state switching (Type=2 Cmd=22): stand, lie down, soft estop
- Gait switching (Type=2 Cmd=23)
- Axis control (Type=2 Cmd=21): forward/backward/left/right/rotate
- Light control (Type=1101 Cmd=2)
- Mode switching (Type=1101 Cmd=5)
- Auto charge (Type=2 Cmd=24)
- Sleep mode (Type=1101 Cmd=6)

Safety requirements:
- Motion state switch requires control_enabled=True
- Axis control requires RL control mode (MotionState=17)
- Soft estop is highest priority, can be sent from any state
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc

from backend.app.protocol.messages import PatrolMessage
from backend.app.utils.safety import detect_protective_fault

logger = logging.getLogger(__name__)


# Motion state constants (V1.2.1 §1.2.3)
MOTION_STATE_IDLE = 0
MOTION_STATE_STAND = 1
MOTION_STATE_SOFT_ESTOP = 2
MOTION_STATE_STARTUP_DAMPING = 3
MOTION_STATE_LIE_DOWN = 4
MOTION_STATE_RL_CONTROL = 17


# Gait constants (V1.2.1 §1.2.4)
GAIT_BASIC_STANDARD = 0x1001      # 基础（标准）
GAIT_PLATFORM_AGGRESSIVE = 0x3002  # 平地（敏捷）
GAIT_STAIRS_AGGRESSIVE = 0x3003    # 楼梯（敏捷）


# Charge state constants (V1.2.1 §1.2.7)
CHARGE_END = 0
CHARGE_START = 1
CHARGE_CLEAR = 2


class MotionControlError(RuntimeError):
    """Raised when motion control command fails."""


@dataclass(frozen=True)
class MotionSafetySnapshot:
    """Safety state for motion control operations."""
    control_enabled: bool
    tcp_connected: bool
    hard_estop_active: bool
    protective_fault_active: bool
    battery_percent: int
    motion_state: int  # Current motion state from basic_status


class MotionControlService:
    """Service for sending motion control commands to M20 Pro.
    
    Commands require explicit Web UI authorization before sending.
    Safety checks are performed before each command.
    """
    
    def __init__(self, client, safety: MotionSafetySnapshot) -> None:
        self._client = client
        self._safety = safety
        self._authorized: bool = False
        self._authorized_by: str = ""
        self._audit_log: list[dict[str, Any]] = []
    
    @property
    def is_authorized(self) -> bool:
        return self._authorized
    
    @property
    def audit_log(self) -> list[dict[str, Any]]:
        return list(self._audit_log)
    
    def authorize(self, operator: str) -> dict[str, Any]:
        """Authorize motion control via Web UI."""
        self._authorized = True
        self._authorized_by = operator
        self._log("authorize", f"Operator: {operator}", True)
        logger.info("运动控制授权成功: %s", operator)
        return {"status": "authorized", "operator": operator}
    
    def deauthorize(self) -> dict[str, Any]:
        """Deauthorize motion control."""
        self._authorized = False
        self._authorized_by = ""
        self._log("deauthorize", "Motion control disabled", True)
        logger.info("运动控制授权已撤销")
        return {"status": "deauthorized"}
    
    def update_safety(self, telemetry_data: dict[str, Any]) -> None:
        """Update safety snapshot from telemetry data."""
        basic = telemetry_data.get("basic", {})
        errors = telemetry_data.get("errors", [])
        
        self._safety = MotionSafetySnapshot(
            control_enabled=self._safety.control_enabled,
            tcp_connected=telemetry_data.get("tcp_connected", False),
            hard_estop_active=basic.get("hes") == 1,
            protective_fault_active=detect_protective_fault(errors),
            battery_percent=telemetry_data.get("battery_percent", 100),
            motion_state=basic.get("motion_state", 0),
        )
    
    def motion_state_switch(self, state: int) -> dict[str, Any]:
        """Switch robot motion state.
        
        Args:
            state: MOTION_STATE_IDLE, MOTION_STATE_STAND, MOTION_STATE_LIE_DOWN, 
                   MOTION_STATE_SOFT_ESTOP, MOTION_STATE_RL_CONTROL
        """
        if not self._check_safety():
            return {"status": "error", "message": "Safety check failed"}
        
        if not self._authorized:
            return {"status": "error", "message": "Motion control not authorized"}
        
        try:
            msg = PatrolMessage(
                message_type=2,
                command=22,
                sent_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                items={"MotionParam": state},
            )
            response = self._client.send_control(msg)
            self._log("motion_state_switch", f"State -> {state}", True)
            logger.info("运动状态切换成功: %s", state)
            return {"status": "ok", "state": state}
        except Exception as e:
            self._log("motion_state_switch", f"Failed: {e}", False)
            return {"status": "error", "message": str(e)}
    
    def gait_switch(self, gait: int) -> dict[str, Any]:
        """Switch robot gait.
        
        Args:
            gait: GAIT_BASIC_STANDARD, GAIT_PLATFORM_AGGRESSIVE, GAIT_STAIRS_AGGRESSIVE
        """
        if not self._check_safety():
            return {"status": "error", "message": "Safety check failed"}
        
        if not self._authorized:
            return {"status": "error", "message": "Motion control not authorized"}
        
        try:
            msg = PatrolMessage(
                message_type=2,
                command=23,
                sent_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                items={"GaitParam": gait},
            )
            response = self._client.send_control(msg)
            self._log("gait_switch", f"Gait -> {gait:#x}", True)
            logger.info("步态切换成功: %s", hex(gait))
            return {"status": "ok", "gait": gait}
        except Exception as e:
            self._log("gait_switch", f"Failed: {e}", False)
            return {"status": "error", "message": str(e)}
    
    def axis_control(self, x: float, y: float, yaw: float) -> dict[str, Any]:
        """Send axis control command (velocity control).
        
        Args:
            x: Forward/backward speed [-1, 1]
            y: Left/right speed [-1, 1]
            yaw: Rotation speed [-1, 1]
        """
        if not self._check_safety():
            return {"status": "error", "message": "Safety check failed"}
        
        if not self._authorized:
            return {"status": "error", "message": "Motion control not authorized"}
        
        # Axis control requires RL control mode
        if self._safety.motion_state != MOTION_STATE_RL_CONTROL:
            return {"status": "error", "message": f"Requires RL control mode (current: {self._safety.motion_state})"}
        
        # Validate range
        for name, value in [("x", x), ("y", y), ("yaw", yaw)]:
            if not -1.0 <= value <= 1.0:
                return {"status": "error", "message": f"{name} must be in [-1, 1]"}
        
        try:
            msg = PatrolMessage(
                message_type=2,
                command=21,
                sent_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                items={"X": x, "Y": y, "Yaw": yaw},
            )
            response = self._client.send_control(msg)
            self._log("axis_control", f"X={x}, Y={y}, Yaw={yaw}", True)
            logger.info("轴指令发送成功: X=%s, Y=%s, Yaw=%s", x, y, yaw)
            return {"status": "ok", "x": x, "y": y, "yaw": yaw}
        except Exception as e:
            self._log("axis_control", f"Failed: {e}", False)
            return {"status": "error", "message": str(e)}
    
    def light_control(self, front: int, back: int) -> dict[str, Any]:
        """Control robot lights.
        
        Args:
            front: Front light (0=off, 1=on)
            back: Back light (0=off, 1=on)
        """
        if not self._check_safety():
            return {"status": "error", "message": "Safety check failed"}
        
        if not self._authorized:
            return {"status": "error", "message": "Motion control not authorized"}
        
        try:
            msg = PatrolMessage(
                message_type=1101,
                command=2,
                sent_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                items={"Front": front, "Back": back},
            )
            response = self._client.send_control(msg)
            self._log("light_control", f"Front={front}, Back={back}", True)
            logger.info("照明灯控制成功")
            return {"status": "ok", "front": front, "back": back}
        except Exception as e:
            self._log("light_control", f"Failed: {e}", False)
            return {"status": "error", "message": str(e)}
    
    def mode_switch(self, mode: int) -> dict[str, Any]:
        """Switch robot usage mode.
        
        Args:
            mode: 0=常规模式, 1=导航模式, 2=辅助模式
        """
        if not self._check_safety():
            return {"status": "error", "message": "Safety check failed"}
        
        if not self._authorized:
            return {"status": "error", "message": "Motion control not authorized"}
        
        try:
            msg = PatrolMessage(
                message_type=1101,
                command=5,
                sent_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                items={"Mode": mode},
            )
            response = self._client.send_control(msg)
            self._log("mode_switch", f"Mode -> {mode}", True)
            logger.info("使用模式切换成功: %s", mode)
            return {"status": "ok", "mode": mode}
        except Exception as e:
            self._log("mode_switch", f"Failed: {e}", False)
            return {"status": "error", "message": str(e)}
    
    def charge_control(self, charge: int) -> dict[str, Any]:
        """Control auto charge.
        
        Args:
            charge: CHARGE_END=0, CHARGE_START=1, CHARGE_CLEAR=2
        """
        if not self._check_safety():
            return {"status": "error", "message": "Safety check failed"}
        
        if not self._authorized:
            return {"status": "error", "message": "Motion control not authorized"}
        
        try:
            msg = PatrolMessage(
                message_type=2,
                command=24,
                sent_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                items={"Charge": charge},
            )
            response = self._client.send_control(msg)
            self._log("charge_control", f"Charge -> {charge}", True)
            logger.info("自主充电控制成功: %s", charge)
            return {"status": "ok", "charge": charge}
        except Exception as e:
            self._log("charge_control", f"Failed: {e}", False)
            return {"status": "error", "message": str(e)}
    
    def sleep_mode(self, sleep: bool, auto: bool = False, time: int = 10) -> dict[str, Any]:
        """Set sleep mode.
        
        Args:
            sleep: True=enter sleep, False=wake up
            auto: Auto sleep enabled
            time: Sleep wait time [5, 30] minutes
        """
        if not self._check_safety():
            return {"status": "error", "message": "Safety check failed"}
        
        if not self._authorized:
            return {"status": "error", "message": "Motion control not authorized"}
        
        if not 5 <= time <= 30:
            return {"status": "error", "message": "Time must be in [5, 30] minutes"}
        
        try:
            msg = PatrolMessage(
                message_type=1101,
                command=6,
                sent_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                items={"Sleep": sleep, "Auto": auto, "Time": time},
            )
            response = self._client.send_control(msg)
            self._log("sleep_mode", f"Sleep={sleep}, Auto={auto}, Time={time}", True)
            logger.info("休眠模式设置成功")
            return {"status": "ok", "sleep": sleep, "auto": auto, "time": time}
        except Exception as e:
            self._log("sleep_mode", f"Failed: {e}", False)
            return {"status": "error", "message": str(e)}
    
    def get_status(self) -> dict[str, Any]:
        """Get motion control service status."""
        return {
            "authorized": self._authorized,
            "authorized_by": self._authorized_by,
            "control_enabled": self._safety.control_enabled,
            "tcp_connected": self._safety.tcp_connected,
            "hard_estop_active": self._safety.hard_estop_active,
            "protective_fault_active": self._safety.protective_fault_active,
            "battery_percent": self._safety.battery_percent,
            "motion_state": self._safety.motion_state,
            "audit_log_count": len(self._audit_log),
        }
    
    def _check_safety(self) -> bool:
        """Check safety conditions before sending command."""
        if not self._safety.control_enabled:
            logger.warning("控制未启用")
            return False
        if not self._safety.tcp_connected:
            logger.warning("TCP未连接")
            return False
        if self._safety.hard_estop_active:
            logger.warning("硬急停已触发")
            return False
        if self._safety.protective_fault_active:
            logger.warning("保护故障激活")
            return False
        if self._safety.battery_percent < 20:
            logger.warning("电量低于20%%")
            return False
        return True
    
    def _log(self, action: str, details: str, success: bool) -> None:
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "action": action,
            "details": details,
            "success": success,
        }
        self._audit_log.append(log_entry)
        if len(self._audit_log) > 100:
            self._audit_log = self._audit_log[-100:]
