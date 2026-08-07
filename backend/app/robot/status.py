"""Status message parser for M20 Pro basic_server protocol.

Based on V1.2.1 developer handbook (2026-05-18) sections 1.3 and 1.4:
- Type 1002 / Command 6: BasicStatus (2Hz heartbeat)
- Type 1002 / Command 4: MotionStatus (10Hz heartbeat)
- Type 1002 / Command 5: DeviceStatus (2Hz heartbeat)
- Type 1002 / Command 3: ErrorList (event-driven)
- Type 1007 / Command 2: Position query response
- Type 2002 / Command 1: Perception state query response
- Type 1003 / Command 1: Navigation task response
- Type 1004 / Command 1: Navigation cancel response
- Type 1007 / Command 1: Navigation status query response
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.protocol.messages import PatrolMessage


class StatusMessageError(ValueError):
    """Raised when a status message cannot be parsed."""


@dataclass(frozen=True)
class StatusResult:
    kind: str
    data: dict[str, Any]


# Official V1.2.1 status message handlers
_COMMAND_BASIC_STATUS = 6
_COMMAND_MOTION_STATUS = 4
_COMMAND_DEVICE_STATUS = 5
_COMMAND_ERROR_LIST = 3
_COMMAND_POSITION = 2
_COMMAND_PERCEPTION = 1
_COMMAND_NAV_RESPONSE = 1
_COMMAND_NAV_CANCEL = 1
_COMMAND_NAV_STATUS = 1
# V1.2.1: navigation abnormal status active report (≥V1.1.8)
_COMMAND_NAV_ABNORMAL = 3

# V1.2.1 navigation error codes (hex)
NAV_ERROR_CODES = {
    0x0000: "导航任务正常状态",
    0x2300: "单点巡检任务执行完成",
    0x2302: "单点巡检任务被取消",
    0x8605: "移动到点超时",
    0xA301: "运动状态异常，任务失败(软急停、摔倒)",
    0xA302: "电量低于20%，任务失败",
    0xA303: "电机过温异常，任务失败",
    0xA305: "雷达异常（未开启或无点云数据）",
    0xA312: "导航模块通讯异常，无法下发任务",
    0xA313: "定位状态持续异常(超过30s)",
    0xA314: "地形图异常",
    0xA327: "步态异常，未切换到目标步态",
    0xA328: "切换导航模式失败",
    0xA341: "当前正在执行任务，下发新任务失败",
    0xA343: "退出自主充电执行失败",
    0xA344: "自主充电异常",
    0xA345: "自主充电执行失败",
    0xA349: "切换地图失败",
    0xA34B: "持续停障异常，导航失败",
    0xA34C: "局部导航规划失败",
    0xA34D: "持续导航速度未刷新，导航失败",
    0xA34E: "自主充电流程中，下发任务失败",
    0xA400: "发送目标点到局部导航失败",
    0xA401: "发送目标点到全局导航失败",
    0xA402: "取消局部导航失败",
    0xA403: "取消全局导航失败",
    0xA404: "导航参数设置失败",
    0xA405: "局部导航模块异常，已重启",
    0xA406: "局部导航模块异常：无实时障碍地图",
    0xA407: "局部导航模块异常：无定位数据",
    0xA408: "全局导航模块异常，已重启",
    0xA409: "全局导航模块异常：无栅格地图",
    0xA40A: "全局导航模块异常：无定位数据",
    0xA40B: "全局导航模块异常：全局导航规划失败",
    0xA40C: "全局导航模块异常：目标点在障碍物中",
    0xA40D: "定位模块异常，已重启",
    0xA40E: "定位模块异常：传感器异常",
    0xA40F: "里程计模块异常：里程计结果发布时间异常",
}


def parse_status_message(message: PatrolMessage) -> StatusResult:
    """Parse an official status/navigation message from the M20 Pro.

    Returns a StatusResult with kind and normalized data fields.
    Raises StatusMessageError for malformed or unsupported messages.
    """
    if message.message_type == 1002:
        return _parse_1002(message)
    if message.message_type == 1003 and message.command == _COMMAND_NAV_RESPONSE:
        return _parse_navigation_response(message)
    if message.message_type == 1004 and message.command == _COMMAND_NAV_CANCEL:
        return _parse_cancel_response(message)
    if message.message_type == 1007 and message.command == _COMMAND_POSITION:
        return _parse_position(message)
    if message.message_type == 2002 and message.command == _COMMAND_PERCEPTION:
        return _parse_perception(message)
    if message.message_type == 1007 and message.command == _COMMAND_NAV_STATUS:
        return _parse_navigation_status(message)
    if message.message_type == 1007 and message.command == _COMMAND_NAV_ABNORMAL:
        return _parse_navigation_abnormal(message)
    raise StatusMessageError(
        f"unsupported status message type={message.message_type}, command={message.command}"
    )


def _parse_1002(message: PatrolMessage) -> StatusResult:
    cmd = message.command
    items = message.items

    if cmd == _COMMAND_BASIC_STATUS:
        return StatusResult("basic_status", _normalize_basic(items))
    if cmd == _COMMAND_MOTION_STATUS:
        return StatusResult("motion_status", _normalize_motion(items))
    if cmd == _COMMAND_DEVICE_STATUS:
        return StatusResult("device_status", _normalize_device(items))
    if cmd == _COMMAND_ERROR_LIST:
        return StatusResult("error_list", _normalize_errors(items))
    raise StatusMessageError(f"1002 unsupported command: {cmd}")


def _normalize_basic(items: dict[str, Any]) -> dict[str, Any]:
    bs = items.get("BasicStatus", {})
    if not isinstance(bs, dict):
        raise StatusMessageError("BasicStatus must be an object")
    return {
        "motion_state": bs.get("MotionState"),
        "gait": bs.get("Gait"),
        "charge": bs.get("Charge"),
        "hes": bs.get("HES"),
        "control_usage_mode": bs.get("ControlUsageMode"),
        "direction": bs.get("Direction"),
        "ooa": bs.get("OOA"),
        "power_management": bs.get("PowerManagement"),
        "sleep": bs.get("Sleep"),
        "version": bs.get("Version"),
    }


def _normalize_motion(items: dict[str, Any]) -> dict[str, Any]:
    ms = items.get("MotionStatus", {})
    if not isinstance(ms, dict):
        raise StatusMessageError("MotionStatus must be an object")
    return {
        "roll": ms.get("Roll"),
        "pitch": ms.get("Pitch"),
        "yaw": ms.get("Yaw"),
        "omega_z": ms.get("OmegaZ"),
        "linear_x": ms.get("LinearX"),
        "linear_y": ms.get("LinearY"),
        "height": ms.get("Height"),
        "payload": ms.get("Payload"),
        "remain_mile": ms.get("RemainMile"),
    }


def _normalize_device(items: dict[str, Any]) -> dict[str, Any]:
    """V1.2.1 DeviceStatus format with BatteryList and arrays."""
    return {
        "battery_list": items.get("BatteryList"),
        "battery_status": items.get("BatteryStatus"),
        "device_temperature": items.get("DeviceTemperature"),
        "led": items.get("Led"),
        "gps": items.get("GPS"),
        "dev_enable": items.get("DevEnable"),
        "cpu": items.get("CPU"),
    }


def _normalize_errors(items: dict[str, Any]) -> dict[str, Any]:
    error_list = items.get("ErrorList")
    if not isinstance(error_list, list):
        raise StatusMessageError("ErrorList must be an array")
    return {
        "errors": [
            {"error_code": e.get("errorCode"), "component": e.get("component")}
            for e in error_list
            if isinstance(e, dict)
        ]
    }


def _parse_position(message: PatrolMessage) -> StatusResult:
    items = message.items
    return StatusResult("position", {
        "location": items.get("Location"),
        "pos_x": items.get("PosX"),
        "pos_y": items.get("PosY"),
        "pos_z": items.get("PosZ"),
        "roll": items.get("Roll"),
        "pitch": items.get("Pitch"),
        "yaw": items.get("Yaw"),
    })


def _parse_perception(message: PatrolMessage) -> StatusResult:
    items = message.items
    return StatusResult("perception", {
        "location": items.get("Location"),
        "obstacle_state": items.get("ObsState"),
    })


def _parse_navigation_response(message: PatrolMessage) -> StatusResult:
    items = message.items
    error_code = items.get("ErrorCode", 0)
    return StatusResult("navigation_response", {
        "value": items.get("Value"),
        "status": items.get("Status"),
        "error_code": error_code,
        "error_message": NAV_ERROR_CODES.get(error_code, "Unknown"),
    })


def _parse_cancel_response(message: PatrolMessage) -> StatusResult:
    items = message.items
    return StatusResult("cancel_response", {
        "error_code": items.get("ErrorCode"),
    })


def _parse_navigation_status(message: PatrolMessage) -> StatusResult:
    items = message.items
    error_code = items.get("ErrorCode", 0)
    return StatusResult("navigation_status", {
        "value": items.get("Value"),
        "status": items.get("Status"),
        "error_code": error_code,
        "error_message": NAV_ERROR_CODES.get(error_code, "Unknown"),
    })


def _parse_navigation_abnormal(message: PatrolMessage) -> StatusResult:
    """Parse Type=1007 Command=3 navigation abnormal status active report (≥V1.1.8)."""
    items = message.items
    nav_status = items.get("NavStatus", {})
    location_status = items.get("LocationStatus", {})
    error_code = nav_status.get("ErrorCode", 0)
    return StatusResult("navigation_abnormal", {
        "nav_status": {
            "value": nav_status.get("Value"),
            "status": nav_status.get("Status"),
            "error_code": error_code,
            "error_message": NAV_ERROR_CODES.get(error_code, "Unknown"),
            "loop_count": nav_status.get("LoopCnt"),
            "remaining_count": nav_status.get("RemainingCnt"),
            "name": nav_status.get("Name"),
        },
        "location_status": {
            "location": location_status.get("Location"),
            "pos_x": location_status.get("PosX"),
            "pos_y": location_status.get("PosY"),
            "pos_z": location_status.get("PosZ"),
            "roll": location_status.get("Roll"),
            "pitch": location_status.get("Pitch"),
            "yaw": location_status.get("Yaw"),
        },
    })
