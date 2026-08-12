"""Runtime integration regressions for the Web UI and control boundaries."""

from __future__ import annotations

import http.client
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.app.api.extended_handlers import (
    WorkOrdersCreateHandler,
    WorkOrdersUpdateHandler,
)
from backend.app.api.router import ApiRouter
from backend.app.config import WebServiceConfig
from backend.app.server import M20WebServer
from backend.app.websocket.ws_handler import NavigationWebSocketHandler
from backend.app.motion.handlers import (
    AxisControlHandler,
    ChargeControlHandler,
    GaitSwitchHandler,
    LightControlHandler,
    ModeSwitchHandler,
    MotionStateHandler,
    SleepModeHandler,
)


@pytest.fixture
def runtime_server(tmp_path: Path):
    config = WebServiceConfig(
        host="127.0.0.1",
        port=8080,
        aos_host="10.21.31.103",
        runtime_mode="simulated",
        read_only_mode=True,
        control_enabled=False,
        allow_real_io=False,
        static_root=str(Path(__file__).parents[2] / "docs" / "website"),
        auth_db_path=str(tmp_path / "auth.db"),
    )
    app = M20WebServer(config)
    app.setup()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), app._create_handler())
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield app, httpd.server_address
    finally:
        httpd.shutdown()
        httpd.server_close()
        if app.gimbal_adapter:
            app.gimbal_adapter.close()


def request(address, method: str, path: str, body: dict | None = None, headers=None):
    connection = http.client.HTTPConnection(*address, timeout=3)
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    request_headers = dict(headers or {})
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
        request_headers["Content-Length"] = str(len(payload))
    connection.request(method, path, body=payload, headers=request_headers)
    response = connection.getresponse()
    data = response.read()
    result = response.status, dict(response.getheaders()), data
    connection.close()
    return result


@pytest.mark.parametrize(
    ("path", "content_type"),
    [
        ("/js/state-manager.js", "text/javascript"),
        ("/js/app.js", "text/javascript"),
        ("/robot-dog.jpg", "image/jpeg"),
    ],
)
def test_static_assets_are_served(runtime_server, path: str, content_type: str):
    _, address = runtime_server

    status, headers, body = request(address, "GET", path)

    assert status == 200
    assert headers["Content-Type"].startswith(content_type)
    assert body


def test_login_returns_valid_response_and_session_cookie(runtime_server):
    _, address = runtime_server

    status, headers, body = request(
        address,
        "POST",
        "/api/v1/auth/login",
        {"username": "admin", "password": "123456"},
    )
    payload = json.loads(body)

    assert status == 200
    assert headers["Set-Cookie"].startswith("m20_session=")
    assert payload["status"] == "success"
    assert payload["data"]["username"] == "admin"
    assert payload["data"]["role"] == "admin"


def test_logout_returns_valid_response_and_clears_cookie(runtime_server):
    _, address = runtime_server
    _, login_headers, _ = request(
        address,
        "POST",
        "/api/v1/auth/login",
        {"username": "admin", "password": "123456"},
    )
    cookie = login_headers["Set-Cookie"].split(";", 1)[0]

    status, headers, body = request(
        address,
        "POST",
        "/api/v1/auth/logout",
        headers={"Cookie": cookie},
    )

    assert status == 200
    assert headers["Set-Cookie"].startswith("m20_session=;")
    assert json.loads(body)["data"]["status"] == "logged_out"


def test_router_resolves_work_order_write_handlers():
    assert ApiRouter.resolve_handler("POST", "/api/v1/work-orders") is WorkOrdersCreateHandler
    assert ApiRouter.resolve_handler("PUT", "/api/v1/work-orders/WO-2026-001") is WorkOrdersUpdateHandler


def test_server_initializes_live_websocket_handlers(runtime_server):
    app, _ = runtime_server

    assert app.ws_upgrade_handler is not None
    assert app.ws_upgrade_handler._video_handler is not None
    assert app.ws_upgrade_handler._nav_handler is not None


def test_auth_enabled_switch_is_applied(tmp_path):
    config = WebServiceConfig(
        runtime_mode="simulated", aos_host="10.21.31.103", auth_enabled=False, auth_db_path=str(tmp_path / "auth.db")
    )
    app = M20WebServer(config)
    app.setup()
    assert app.auth_middleware is not None
    assert app.auth_middleware.allow_anonymous is True


def test_manifest_does_not_contain_gimbal_password():
    manifest = Path(__file__).parents[2] / "deploy" / "readonly-manifest.json"
    assert "gimbal_password" not in manifest.read_text(encoding="utf-8")


def test_server_safety_callbacks_include_top_level_battery(runtime_server):
    app, _ = runtime_server
    nav_update = MagicMock()
    motion_update = MagicMock()
    app.nav_service.update_safety_from_telemetry = nav_update
    app.motion_service.update_safety = motion_update

    app._register_safety_callbacks()
    payload = {
        "tcp_connected": True,
        "battery_percent": 76,
        "data": {"basic": {"hes": 0}, "errors": []},
    }
    app.telemetry_adapter._nav_sync_callback(payload)
    app.telemetry_adapter._motion_sync_callback(payload)

    assert nav_update.call_args.args[0]["battery_percent"] == 76
    assert motion_update.call_args.args[0]["battery_percent"] == 76
    assert nav_update.call_args.args[0]["tcp_connected"] is True


def test_navigation_websocket_rejects_control_actions():
    import asyncio

    nav_service = object()
    handler = NavigationWebSocketHandler(nav_service)

    result = asyncio.run(handler.handle_message(json.dumps({"action": "authorize"})))

    assert result == {
        "type": "error",
        "code": "control_over_websocket_disabled",
        "message": "控制操作必须通过经过认证的 HTTP API 执行",
    }


@pytest.mark.parametrize(
    "handler_class",
    [
        MotionStateHandler,
        GaitSwitchHandler,
        AxisControlHandler,
        LightControlHandler,
        ModeSwitchHandler,
        ChargeControlHandler,
        SleepModeHandler,
    ],
)
def test_motion_control_actions_require_admin_role(handler_class):
    handler = handler_class.__new__(handler_class)
    handler.config = SimpleNamespace(control_enabled=True, read_only_mode=False)
    handler._authenticate = MagicMock(
        return_value=SimpleNamespace(role="viewer", user=SimpleNamespace(username="viewer"))
    )
    handler.send_error_response = MagicMock()
    handler._parse_json_body = MagicMock(return_value={})
    handler.server_instance = SimpleNamespace(motion_service=MagicMock())

    handler.do_POST()

    handler.send_error_response.assert_called_once_with(403, "需要管理员权限")
    assert not handler.server_instance.motion_service.mock_calls
