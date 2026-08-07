"""Test status message parser against V1.2.1 handbook."""

import pytest

from backend.app.protocol.messages import PatrolMessage
from backend.app.robot.status import (
    StatusMessageError,
    parse_status_message,
    NAV_ERROR_CODES,
)


def test_parses_v121_basic_status_message():
    """Test BasicStatus parsing with V1.2.1 field format."""
    result = parse_status_message(
        PatrolMessage(
            1002,
            6,
            "2026-08-06 14:00:00",
            {
                "BasicStatus": {
                    "MotionState": 1,
                    "Gait": 0x3002,  # V1.2.1: 平地敏捷模式
                    "Charge": 0,
                    "HES": 0,
                    "ControlUsageMode": 1,
                    "Direction": 0,
                    "OOA": 0,
                    "PowerManagement": 0,
                    "Sleep": 0,
                    "Version": "PRO",
                }
            },
        )
    )

    assert result.kind == "basic_status"
    assert result.data["motion_state"] == 1
    assert result.data["gait"] == 0x3002
    assert result.data["version"] == "PRO"


def test_parses_v121_device_status_with_battery_list():
    """Test DeviceStatus parsing with V1.2.1 BatteryList array."""
    result = parse_status_message(
        PatrolMessage(
            1002,
            5,
            "2026-08-06 14:00:00",
            {
                "BatteryList": [
                    {
                        "Voltage": 25.5,
                        "BatteryLevel": 85.0,
                        "battery_temperature": 28.5,
                        "charge": False,
                        "serial": "B001",
                    },
                    {
                        "Voltage": 25.8,
                        "BatteryLevel": 90.0,
                        "battery_temperature": 27.2,
                        "charge": False,
                        "serial": "B002",
                    },
                ],
                "BatteryStatus": {
                    "VoltageLeft": 25.5,
                    "VoltageRight": 25.8,
                    "BatteryLevelLeft": 85.0,
                    "BatteryLevelRight": 90.0,
                    "chargeLeft": False,
                    "chargeRight": False,
                },
                "DeviceTemperature": {
                    "Motor": [0.0] * 16,
                    "Driver": [0.0] * 16,
                    "LeftFrontHipXMotor": 45.0,
                    "LeftFrontHipXDriver": 42.0,
                },
                "Led": {"Fill": {"Front": 1, "Back": 1}},
                "GPS": {
                    "Latitude": 23.123,
                    "Longitude": 113.456,
                    "Speed": 0.0,
                    "Course": 0.0,
                    "FixQuality": 1.0,
                    "NumSatellites": 8,
                    "Altitude": 10.0,
                    "HDOP": 1.0,
                    "VDOP": 1.0,
                    "PDOP": 1.0,
                    "VisibleSatellites": 8,
                },
                "DevEnable": {
                    "FanSpeed": 100,
                    "LoadPower": 1,
                    "LedHost": 1,
                    "LedExt": 1,
                    "FP": 1,
                    "Lidar": {"Front": 1, "Back": 1},
                    "GPS": 1,
                    "Video": {"Front": 1, "Back": 1},
                },
                "CPU": {
                    "AOS": {"Temperature": 55.0, "FrequencyInt": 30.0, "FrequencyApp": 45.0},
                    "NOS": {"Temperature": 52.0, "FrequencyInt": 25.0, "FrequencyApp": 40.0},
                    "GOS": {"Temperature": 48.0, "FrequencyInt": 20.0, "FrequencyApp": 35.0},
                },
            },
        )
    )

    assert result.kind == "device_status"
    assert len(result.data["battery_list"]) == 2
    assert result.data["battery_list"][0]["serial"] == "B001"
    assert result.data["battery_list"][1]["BatteryLevel"] == 90.0
    assert result.data["cpu"]["GOS"]["Temperature"] == 48.0


def test_parses_navigation_response_with_error_codes():
    """Test navigation response with V1.2.1 error code lookup."""
    result = parse_status_message(
        PatrolMessage(
            1003,
            1,
            "2026-08-06 14:00:00",
            {"Value": 0, "Status": 4, "ErrorCode": 0x2300},
        )
    )

    assert result.kind == "navigation_response"
    assert result.data["error_code"] == 0x2300
    assert result.data["error_message"] == "单点巡检任务执行完成"


def test_parses_navigation_status_with_error():
    """Test navigation status with error code lookup."""
    result = parse_status_message(
        PatrolMessage(
            1007,
            1,
            "2026-08-06 14:00:00",
            {"Value": 0, "Status": 0, "ErrorCode": 0xA301},
        )
    )

    assert result.kind == "navigation_status"
    assert result.data["error_code"] == 0xA301
    assert result.data["error_message"] == "运动状态异常，任务失败(软急停、摔倒)"


def test_error_list_parsing():
    """Test ErrorList parsing with V1.2.1 format."""
    result = parse_status_message(
        PatrolMessage(
            1002,
            3,
            "2026-08-06 14:00:00",
            {
                "ErrorList": [
                    {"errorCode": 0x8001, "component": 0x01},
                    {"errorCode": 0x8102, "component": 0x00},
                ]
            },
        )
    )

    assert result.kind == "error_list"
    assert len(result.data["errors"]) == 2
    assert result.data["errors"][0]["error_code"] == 0x8001
    assert result.data["errors"][0]["component"] == 0x01


def test_position_query_response():
    """Test position query response."""
    result = parse_status_message(
        PatrolMessage(
            1007,
            2,
            "2026-08-06 14:00:00",
            {
                "Location": 0,
                "PosX": 1.5,
                "PosY": 2.3,
                "PosZ": 0.0,
                "Roll": 0.0,
                "Pitch": 0.0,
                "Yaw": 1.57,
            },
        )
    )

    assert result.kind == "position"
    assert result.data["pos_x"] == 1.5
    assert result.data["location"] == 0


def test_perception_query_response():
    """Test perception query response."""
    result = parse_status_message(
        PatrolMessage(
            2002,
            1,
            "2026-08-06 14:00:00",
            {"Location": 0, "ObsState": 1},
        )
    )

    assert result.kind == "perception"
    assert result.data["obstacle_state"] == 1


def test_rejects_malformed_basic_status():
    """Test rejection of malformed BasicStatus."""
    with pytest.raises(StatusMessageError):
        parse_status_message(
            PatrolMessage(1002, 6, "2026-08-06 14:00:00", {"BasicStatus": "not_a_dict"})
        )


def test_rejects_unsupported_message():
    """Test rejection of unsupported message type."""
    with pytest.raises(StatusMessageError, match="unsupported"):
        parse_status_message(PatrolMessage(9999, 1, "2026-08-06 14:00:00", {}))


def test_cancel_response():
    """Test cancel response parsing."""
    result = parse_status_message(
        PatrolMessage(
            1004,
            1,
            "2026-08-06 14:00:00",
            {"ErrorCode": 0},
        )
    )

    assert result.kind == "cancel_response"
    assert result.data["error_code"] == 0


def test_nav_error_codes_complete():
    """Test that all documented V1.2.1 navigation error codes are known."""
    # Check some key codes
    assert 0x2300 in NAV_ERROR_CODES
    assert 0xA301 in NAV_ERROR_CODES
    assert 0xA34C in NAV_ERROR_CODES


def test_parses_navigation_abnormal_report():
    """Test Type=1007 Command=3 navigation abnormal status active report (≥V1.1.8)."""
    result = parse_status_message(
        PatrolMessage(
            1007,
            3,
            "2026-08-06 14:00:00",
            {
                "NavStatus": {
                    "Value": 0,
                    "Status": 3,
                    "ErrorCode": 0xA313,
                    "LoopCnt": 5,
                    "RemainingCnt": 0,
                    "Name": "patrol_route_1",
                },
                "LocationStatus": {
                    "Location": 1,
                    "PosX": 1.5,
                    "PosY": 2.3,
                    "PosZ": 0.0,
                    "Roll": 0.0,
                    "Pitch": 0.0,
                    "Yaw": 1.57,
                },
            },
        )
    )

    assert result.kind == "navigation_abnormal"
    assert result.data["nav_status"]["error_code"] == 0xA313
    assert result.data["nav_status"]["error_message"] == "定位状态持续异常(超过30s)"
    assert result.data["nav_status"]["loop_count"] == 5
    assert result.data["nav_status"]["name"] == "patrol_route_1"
    assert result.data["location_status"]["location"] == 1
    assert result.data["location_status"]["pos_x"] == 1.5
    assert result.data["location_status"]["yaw"] == 1.57
