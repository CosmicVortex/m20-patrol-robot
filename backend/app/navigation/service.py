"""Web API for navigation control with manual authorization.

Navigation commands require explicit Web UI authorization before sending.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
# Python 3.8 compatibility: UTC was added in Python 3.11
try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc
from typing import Any

from backend.app.navigation.v010 import (
    SinglePointNavigation,
    NavigationSafetySnapshot,
    NavigationInterlockError,
)
from backend.app.robot.basic_client import BasicServerClient, BasicServerConfig
from backend.app.protocol.messages import PatrolMessage

logger = logging.getLogger(__name__)


@dataclass
class NavigationAuthorization:
    """Web UI authorization state for navigation."""
    authorized: bool = False
    authorized_at: str = ""
    authorized_by: str = ""
    authorization_note: str = ""


@dataclass
class NavigationAuditLog:
    """Audit log for navigation operations."""
    timestamp: str
    action: str  # "authorize", "send", "cancel", "error"
    details: str
    success: bool = False


class NavigationService:
    """Navigation control service with Web authorization."""

    def __init__(self, client: BasicServerClient, safety: NavigationSafetySnapshot) -> None:
        self._client = client
        self._safety = safety
        self._auth = NavigationAuthorization()
        self._audit_log: list[NavigationAuditLog] = []
        self._current_task_id: int = 0

    @staticmethod
    def _detect_protective_fault(errors: list[dict[str, Any]]) -> bool:
        """Detect protective faults from error list.

        V1.2.1 错误码表 - 保护类错误:
        - 0x8002: 电机温度过高保护
        - 0x8008: 驱动器欠压保护
        - 0x8009: 驱动器过压保护
        - 0x8020: 驱动器过流保护
        - 0x8103: 保护电量
        - 0x8106: 电池输出最低电压保护
        - 0x8107-0x8128: 各类电池保护错误
        - 0x8211: CPU 占用率过高保护
        - 0x8212: CPU 温度过高保护
        """
        PROTECTIVE_FAULT_CODES = {
            0x8002, 0x8008, 0x8009, 0x8020,  # 电机/驱动器保护
            0x8103, 0x8106, 0x8107, 0x8108, 0x8112, 0x8115, 0x8116,  # 电池保护
            0x8117, 0x8118, 0x8119, 0x8120, 0x8121, 0x8122,  # 电池保护
            0x8211, 0x8212,  # CPU保护
        }
        for err in errors:
            error_code = err.get("error_code", 0)
            if error_code in PROTECTIVE_FAULT_CODES:
                return True
        return False

    def update_safety_from_telemetry(self, telemetry_data: dict[str, Any]) -> None:
        """Update navigation safety snapshot from telemetry data.

        V1.2.1 §1.3: Status messages include basic_status (1002/6),
        motion_status (1002/4), device_status (1002/5), error_list (1002/3),
        nav_status (1007/1), position (1007/2), perception (2002/1).
        """
        # Extract safety-critical fields from telemetry
        basic = telemetry_data.get("basic", {})
        position = telemetry_data.get("position", {})
        perception = telemetry_data.get("perception", {})
        nav_status = telemetry_data.get("nav_status", {})
        errors = telemetry_data.get("errors", [])

        # Update safety snapshot fields based on telemetry
        self._safety = NavigationSafetySnapshot(
            control_enabled=self._safety.control_enabled,  # Keep configured value
            field_authorization=self._auth.authorized_by if self._auth.authorized else "",
            tcp_connected=telemetry_data.get("tcp_connected", False),
            location_normal=position.get("location") == 0 or bool(position.get("pos_x")),
            obstacle_avoidance_active=perception.get("obstacle_state") == 0,
            hard_estop_active=basic.get("hes") == 1,
            protective_fault_active=self._detect_protective_fault(errors),
            battery_percent=telemetry_data.get("battery_percent", 100),
            active_task=nav_status.get("status") in (2, 3, 4),  # processing/navigating/done
        )

    @property
    def is_authorized(self) -> bool:
        return self._auth.authorized

    @property
    def audit_log(self) -> list[NavigationAuditLog]:
        return list(self._audit_log)

    def authorize(self, operator: str, note: str = "") -> dict[str, Any]:
        """Authorize navigation control via Web UI."""
        self._auth = NavigationAuthorization(
            authorized=True,
            authorized_at=datetime.now(UTC).isoformat(),
            authorized_by=operator,
            authorization_note=note,
        )
        self._log("authorize", f"Operator: {operator}, Note: {note}", True)
        logger.info("导航授权成功: %s", operator)
        return {
            "status": "authorized",
            "operator": operator,
            "authorized_at": self._auth.authorized_at,
        }

    def deauthorize(self) -> dict[str, Any]:
        """Deauthorize navigation control."""
        self._auth = NavigationAuthorization()
        self._log("deauthorize", "Navigation control disabled", True)
        logger.info("导航授权已撤销")
        return {"status": "deauthorized"}

    def send_navigation(self, pos_x: float, pos_y: float, pos_z: float = 0.0, 
                        angle_yaw: float = 0.0, map_id: int = 1) -> dict[str, Any]:
        """Send single-point navigation command."""
        if not self._auth.authorized:
            return {"status": "error", "message": "Navigation not authorized"}
        
        if not self._safety.control_enabled:
            return {"status": "error", "message": "Control not enabled"}
        
        if not self._safety.tcp_connected:
            return {"status": "error", "message": "Not connected to AOS"}

        try:
            nav = SinglePointNavigation(
                value=0,  # V1.2.1: 使用默认值 0
                map_id=0,  # V1.2.1: 使用默认值 0
                pos_x=pos_x,
                pos_y=pos_y,
                pos_z=pos_z,
                angle_yaw=angle_yaw,
            )
            msg = nav.to_message(self._safety, datetime.now(UTC).isoformat())
            
            self._current_task_id += 1
            task_id = self._current_task_id
            
            # Send message (this will connect to AOS)
            try:
                response = self._client.send_control(msg)
                self._log("send", f"Task {task_id}: navigate to ({pos_x}, {pos_y})", True)
                logger.info("导航任务 %s 已发送", task_id)
                return {
                    "status": "sent",
                    "task_id": task_id,
                    "message": f"Navigation to ({pos_x}, {pos_y}) sent",
                }
            except Exception as e:
                self._log("send", f"Task {task_id}: failed - {e}", False)
                return {"status": "error", "message": str(e)}

        except NavigationInterlockError as e:
            self._log("send", f"Safety check failed: {e}", False)
            return {"status": "error", "message": str(e)}
        except Exception as e:
            self._log("send", f"Unexpected error: {e}", False)
            return {"status": "error", "message": str(e)}

    def cancel_navigation(self) -> dict[str, Any]:
        """Cancel current navigation task."""
        if not self._auth.authorized:
            return {"status": "error", "message": "Navigation not authorized"}
        
        if not self._safety.tcp_connected:
            return {"status": "error", "message": "Not connected to AOS"}

        try:
            from backend.app.navigation.v010 import build_cancel_navigation_message
            msg = build_cancel_navigation_message(self._safety, datetime.now(UTC).isoformat())
            
            self._client.send_control(msg)
            self._log("cancel", "Navigation cancelled", True)
            logger.info("导航任务已取消")
            return {"status": "cancelled"}

        except Exception as e:
            self._log("cancel", f"Cancel failed: {e}", False)
            return {"status": "error", "message": str(e)}

    def get_status(self) -> dict[str, Any]:
        """Get navigation service status."""
        return {
            "authorized": self._auth.authorized,
            "authorized_at": self._auth.authorized_at,
            "authorized_by": self._auth.authorized_by,
            "authorization_note": self._auth.authorization_note,
            "control_enabled": self._safety.control_enabled,
            "tcp_connected": self._safety.tcp_connected,
            "current_task_id": self._current_task_id,
            "audit_log_count": len(self._audit_log),
        }

    def _log(self, action: str, details: str, success: bool) -> None:
        log = NavigationAuditLog(
            timestamp=datetime.now(UTC).isoformat(),
            action=action,
            details=details,
            success=success,
        )
        self._audit_log.append(log)
        # Keep only last 100 entries
        if len(self._audit_log) > 100:
            self._audit_log = self._audit_log[-100:]
