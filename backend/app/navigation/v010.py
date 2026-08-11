"""Fail-closed V0.1.0 single-point navigation request model.

Based on V1.2.1 developer handbook (2026-05-18) section 1.4.4.

This module only validates and constructs documented ASDU messages. It does not
open sockets; a caller must separately hold explicit field authorization before
passing the resulting message to a control transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from backend.app.protocol.messages import PatrolMessage

# V1.2.1 official gait constants (hex values)
GAIT_FLAT_AGGRESSIVE = 0x3002  # 平地（敏捷运动模式）
GAIT_STAIRS_AGGRESSIVE = 0x3003  # 楼梯（敏捷运动模式）
GAIT_FLAT_STANDARD = 0x1001  # 基础（标准运动模式）
GAIT_PLATFORM_STANDARD = 0x1002  # 高台（标准运动模式）

# V1.2.1 navigation mode constants
NAV_MODE_STRAIGHT = 0  # 直线导航
NAV_MODE_AUTO = 1  # 自主导航

# V1.2.1 speed constants
SPEED_NORMAL = 0  # 正常
SPEED_SLOW = 1  # 低速
SPEED_HIGH = 2  # 高速

# V1.2.1 point type constants
POINT_TRANSIT = 0  # 过渡点
POINT_TASK = 1  # 任务点
POINT_CHARGE = 3  # 充电点

# V1.2.1 obstacle mode constants
OBSMODE_ON = 0  # 开启停避障
OBSMODE_OFF = 1  # 关闭停避障


class NavigationInterlockError(RuntimeError):
    """Raised when a required field safety condition is absent or unsafe."""


@dataclass(frozen=True)
class NavigationSafetySnapshot:
    control_enabled: bool
    field_authorization: str
    tcp_connected: bool
    location_normal: bool
    obstacle_avoidance_active: bool
    hard_estop_active: bool
    protective_fault_active: bool
    battery_percent: int
    active_task: bool

    def validate_for_navigation(self) -> None:
        for name, value in (
            ("control_enabled", self.control_enabled),
            ("tcp_connected", self.tcp_connected),
            ("location_normal", self.location_normal),
            ("obstacle_avoidance_active", self.obstacle_avoidance_active),
            ("hard_estop_active", self.hard_estop_active),
            ("protective_fault_active", self.protective_fault_active),
            ("active_task", self.active_task),
        ):
            if type(value) is not bool:
                raise NavigationInterlockError(f"{name} must be boolean")
        if not self.control_enabled:
            raise NavigationInterlockError("control is disabled")
        if not self.field_authorization.strip():
            raise NavigationInterlockError("field authorization is required")

        if not self.tcp_connected:
            raise NavigationInterlockError("basic_server TCP is disconnected")
        if not self.location_normal:
            raise NavigationInterlockError("location is not normal")
        if not self.obstacle_avoidance_active:
            raise NavigationInterlockError("obstacle avoidance is not active")
        if self.hard_estop_active:
            raise NavigationInterlockError("hard emergency stop is active")
        if self.protective_fault_active:
            raise NavigationInterlockError("protective fault is active")
        if type(self.battery_percent) is not int or self.battery_percent < 20:
            raise NavigationInterlockError("battery is below the documented safety threshold")
        if self.active_task:
            raise NavigationInterlockError("a navigation task is already active")


@dataclass(frozen=True)
class SinglePointNavigation:
    value: int
    map_id: int
    pos_x: float
    pos_y: float
    pos_z: float
    angle_yaw: float

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value < 0:
            raise ValueError("value must be a non-negative integer")
        if type(self.map_id) is not int or self.map_id < 0:
            raise ValueError("map_id must be a non-negative integer")
        for name, number in (
            ("pos_x", self.pos_x),
            ("pos_y", self.pos_y),
            ("pos_z", self.pos_z),
            ("angle_yaw", self.angle_yaw),
        ):
            if type(number) not in (int, float) or not isfinite(number):
                raise ValueError(f"{name} must be a finite number")

    def to_message(self, safety: NavigationSafetySnapshot, sent_at: str) -> PatrolMessage:
        safety.validate_for_navigation()
        return PatrolMessage(
            message_type=1003,
            command=1,
            sent_at=sent_at,
            items={
                "Value": 0,  # V1.2.1: 使用默认值 0
                "MapID": 0,  # V1.2.1: 使用默认值 0
                "PosX": float(self.pos_x),
                "PosY": float(self.pos_y),
                "PosZ": float(self.pos_z),
                "AngleYaw": float(self.angle_yaw),
                "PointInfo": POINT_TASK,
                "Gait": GAIT_FLAT_AGGRESSIVE,  # V1.2.1: 平地敏捷模式 = 0x3002
                "Speed": SPEED_NORMAL,  # V1.2.1: 正常速度 = 0
                "Manner": 0,  # 前进行走
                "ObsMode": OBSMODE_ON,  # 开启停避障
                "NavMode": NAV_MODE_AUTO,  # 自主导航
            },
        )


def build_cancel_navigation_message(safety: NavigationSafetySnapshot, sent_at: str) -> PatrolMessage:
    """Build the V0.1.0 `1004/1` cancellation request after all gates pass."""
    safety.validate_for_navigation()
    return PatrolMessage(message_type=1004, command=1, sent_at=sent_at, items={})


def build_navigation_status_query(safety: NavigationSafetySnapshot, sent_at: str) -> PatrolMessage:
    """Build the V0.1.0 `1007/1` task status request after all gates pass."""
    safety.validate_for_navigation()
    return PatrolMessage(message_type=1007, command=1, sent_at=sent_at, items={})
