"""Device management handlers for M20 Pro patrol robot web service.

Provides CRUD endpoints for managing robot devices in a JSON file.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc

from backend.app.auth.middleware import AuthMiddleware, AuthRequiredError, AuthResult
from backend.app.auth.store import AuthUser, AuthenticationError, Session, UserStore
from backend.app.api.response import ApiFormatter, RequestContext
from backend.app.api.base_handler import BaseHandler
from backend.app.robot.telemetry import TelemetryAdapter
from backend.app.navigation.service import NavigationService
from backend.app.config import WebServiceConfig
from backend.app.gimbal.adapter import SoarGimbalAdapter

logger = logging.getLogger(__name__)

DEVICES_FILE = os.environ.get(
    "M20_DEVICES_DB",
    str(Path(__file__).parent.parent.parent / "var" / "devices.json"),
)


def _load_devices() -> list[dict[str, Any]]:
    """Load devices from JSON file."""
    try:
        with open(DEVICES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_devices(devices: list[dict[str, Any]]) -> None:
    """Save devices to JSON file."""
    os.makedirs(os.path.dirname(DEVICES_FILE), exist_ok=True)
    with open(DEVICES_FILE, "w", encoding="utf-8") as f:
        json.dump(devices, f, ensure_ascii=False, indent=2)


def _init_default_devices() -> None:
    """Initialize with default devices if file doesn't exist."""
    if os.path.exists(DEVICES_FILE):
        return
    # Default device list with system devices
    default_devices = [
        {"id": "aos", "type": "application_server", "name": "AOS应用服务器", "location": "服务器机房", "ip_address": "10.21.31.103", "status": "configured"},
        {"id": "gos", "type": "guard_operator_station", "name": "GOS守护站", "location": "现场GOS", "ip_address": "10.21.31.104", "status": "configured"},
        {"id": "nos", "type": "navigation_operator_station", "name": "NOS导航站", "location": "现场NOS", "ip_address": "10.21.31.106", "status": "configured"},
    ]
    _save_devices(default_devices)


class DevicesCreateHandler(BaseHandler):
    """POST /api/v1/devices - Create a new device."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/devices":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth:
            return

        if auth.role != "admin":
            self.send_error_response(403, "需要管理员权限")
            return

        body = self._parse_json_body()

        # Validate required fields
        name = body.get("name", "").strip()
        device_type = body.get("type", "").strip()
        ip_address = body.get("ip_address", "").strip()

        if not name or not device_type or not ip_address:
            self.send_error_response(400, "名称、类型和IP地址不能为空")
            return

        _init_default_devices()
        devices = _load_devices()

        # Generate ID based on existing count
        device_id = f"DEV-{datetime.now(UTC).year}-{len(devices) + 1:03d}"

        new_device = {
            "id": device_id,
            "type": device_type,
            "name": name,
            "location": body.get("location", "未指定"),
            "ip_address": ip_address,
            "status": body.get("status", "active"),
            "created_at": datetime.now(UTC).isoformat(),
        }

        devices.append(new_device)
        try:
            _save_devices(devices)
        except (OSError, TypeError, ValueError) as exc:
            logger.error("设备保存失败: %s", exc)
            self.send_error_response(503, "设备保存失败")
            return

        self.send_json_response(201, {"device": new_device})


class DevicesDeleteHandler(BaseHandler):
    """DELETE /api/v1/devices/{id} - Delete a device."""

    def do_DELETE(self) -> None:
        # Parse ID from path: /api/v1/devices/DEV-2026-001
        parts = self.path.strip("/").split("/")
        if len(parts) != 2 or parts[1] == "":
            self.send_error_response(404, "Not found")
            return

        device_id = parts[1]
        auth = self._authenticate()
        if not auth:
            return

        if auth.role != "admin":
            self.send_error_response(403, "需要管理员权限")
            return

        _init_default_devices()
        devices = _load_devices()

        # Find and remove device
        found = False
        updated_devices = []
        for d in devices:
            if d.get("id") == device_id:
                found = True
            else:
                updated_devices.append(d)

        if not found:
            self.send_error_response(404, "设备不存在")
            return

        try:
            _save_devices(updated_devices)
        except (OSError, TypeError, ValueError) as exc:
            logger.error("设备删除失败: %s", exc)
            self.send_error_response(503, "设备删除失败")
            return

        self.send_json_response(200, {"message": "设备已删除", "deleted_id": device_id})
