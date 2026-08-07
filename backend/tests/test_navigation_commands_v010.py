from backend.app.navigation.v010 import (
    NavigationSafetySnapshot,
    build_cancel_navigation_message,
    build_navigation_status_query,
)


def test_builds_v010_cancel_and_status_query_only_after_control_gate():
    safety = NavigationSafetySnapshot(
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

    cancel = build_cancel_navigation_message(safety, "2026-08-06 14:00:00")
    status = build_navigation_status_query(safety, "2026-08-06 14:00:01")

    assert (cancel.message_type, cancel.command, cancel.items) == (1004, 1, {})
    assert (status.message_type, status.command, status.items) == (1007, 1, {})
