import pytest

from backend.app.navigation.v010 import NavigationSafetySnapshot, SinglePointNavigation, NavigationInterlockError


def valid_snapshot() -> NavigationSafetySnapshot:
    return NavigationSafetySnapshot(
        control_enabled=True,
        field_authorization="approved-on-site",
        tcp_connected=True,
        location_normal=True,
        obstacle_avoidance_active=True,
        hard_estop_active=False,
        protective_fault_active=False,
        battery_percent=60,
        active_task=False,
    )


def test_builds_v010_low_speed_autonomous_task_point_request_after_all_gates_pass():
    task = SinglePointNavigation(
        value=7,
        map_id=0,
        pos_x=1.2,
        pos_y=-0.4,
        pos_z=0.0,
        angle_yaw=1.57,
    )

    message = task.to_message(valid_snapshot(), "2026-08-06 14:00:00")

    assert (message.message_type, message.command) == (1003, 1)
    assert message.items == {
        "Value": 7,
        "MapID": 0,
        "PosX": 1.2,
        "PosY": -0.4,
        "PosZ": 0.0,
        "AngleYaw": 1.57,
        "PointInfo": 1,  # POINT_TASK
        "Gait": 0x3002,  # V1.2.1: GAIT_FLAT敏捷 (平地敏捷模式)
        "Speed": 1,  # SPEED_SLOW
        "Manner": 0,  # 前进行走
        "ObsMode": 0,  # OBSMODE_ON (开启停避障)
        "NavMode": 1,  # NAV_MODE_AUTO (自主导航)
    }


@pytest.mark.parametrize(
    "change",
    [
        {"control_enabled": False},
        {"field_authorization": ""},

        {"tcp_connected": False},
        {"location_normal": False},
        {"obstacle_avoidance_active": False},
        {"hard_estop_active": True},
        {"protective_fault_active": True},
        {"battery_percent": 19},
        {"active_task": True},
    ],
)
def test_refuses_navigation_when_any_required_safety_gate_fails(change):
    values = {**valid_snapshot().__dict__, **change}
    task = SinglePointNavigation(1, 0, 0.0, 0.0, 0.0, 0.0)

    with pytest.raises(NavigationInterlockError):
        task.to_message(NavigationSafetySnapshot(**values), "2026-08-06 14:00:00")


@pytest.mark.parametrize("field", [
    "control_enabled", "tcp_connected", "location_normal",
    "obstacle_avoidance_active", "hard_estop_active",
    "protective_fault_active", "active_task",
])
def test_refuses_non_boolean_safety_fields(field):
    values = {**valid_snapshot().__dict__, field: 1}
    with pytest.raises(NavigationInterlockError, match="boolean"):
        NavigationSafetySnapshot(**values).validate_for_navigation()
