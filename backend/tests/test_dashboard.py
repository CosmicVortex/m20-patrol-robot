from pathlib import Path

import pytest

from backend.app.dashboard import DashboardServer, serve_dashboard


def test_dashboard_serves_status_and_dual_camera_placeholders(tmp_path: Path):
    server = DashboardServer(
        title="M20 Patrol / Read-only",
        front_hls_url="/streams/front/index.m3u8",
        rear_hls_url="/streams/rear/index.m3u8",
    )

    page = server.render_index()

    assert "M20 Patrol / Read-only" in page
    assert 'data-camera="front"' in page
    assert 'data-camera="rear"' in page
    assert "/streams/front/index.m3u8" in page
    assert "/streams/rear/index.m3u8" in page
    assert "SIMULATED" in page
    assert "status/latest" in page


def test_dashboard_status_payload_is_explicitly_simulated_until_real_client_exists():
    payload = DashboardServer().status_payload()

    assert payload["source"] == "SIMULATED"
    assert payload["connected"] is False
    assert payload["control_enabled"] is False
    assert payload["data"]["navigation"] == "NOT_CONNECTED"


def test_dashboard_rejects_non_loopback_bind_address():
    with pytest.raises(ValueError, match="127\\.0\\.0\\.1"):
        serve_dashboard(host="0.0.0.0")


def test_dashboard_rejects_invalid_port():
    with pytest.raises(ValueError, match="port"):
        serve_dashboard(port=0)
