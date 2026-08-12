"""Extended API handlers for M20 Pro patrol robot web service.

Adds work order management, inspection point management, timeline data,
and gimbal control endpoints.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Optional
import hashlib
import ipaddress
import secrets
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

WORK_ORDERS_FILE = os.environ.get(
    "M20_WORK_ORDERS_DB",
    str(Path(__file__).parent.parent.parent / "var" / "work_orders.json"),
)


# ── Work Order handlers ──────────────────────────────────────────────────────

def _load_work_orders() -> list[dict[str, Any]]:
    """Load work orders from JSON file."""
    try:
        with open(WORK_ORDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_work_orders(orders: list[dict[str, Any]]) -> None:
    """Save work orders to JSON file."""
    os.makedirs(os.path.dirname(WORK_ORDERS_FILE), exist_ok=True)
    with open(WORK_ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


def _init_default_work_orders() -> None:
    """Initialize with default work orders if file doesn't exist."""
    if os.path.exists(WORK_ORDERS_FILE):
        return
    # No default work orders - let users create their own
    _save_work_orders([])


class WorkOrdersListHandler(BaseHandler):
    """GET /api/v1/work-orders - List work orders."""

    def do_GET(self) -> None:
        if self.path != "/api/v1/work-orders":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth and (not self.auth_middleware or not self.auth_middleware.allow_anonymous):
            return

        _init_default_work_orders()
        orders = _load_work_orders()

        # Filter by status if provided
        status_filter = self.path.split("?")[1] if "?" in self.path else ""
        if "status=" in status_filter:
            status = status_filter.split("status=")[1].split("&")[0]
            orders = [o for o in orders if o.get("status") == status]

        # Summary counts
        summary = {
            "total": len(orders),
            "pending": len([o for o in orders if o.get("status") == "pending"]),
            "in_progress": len([o for o in orders if o.get("status") == "in_progress"]),
            "completed": len([o for o in orders if o.get("status") == "completed"]),
            "high_priority": len([o for o in orders if o.get("priority") == "high" and o.get("status") != "completed"]),
        }

        self.send_json_response(200, {"summary": summary, "orders": orders})


class WorkOrdersCreateHandler(BaseHandler):
    """POST /api/v1/work-orders - Create work order."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/work-orders":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth:
            return

        body = self._parse_json_body()
        title = body.get("title", "").strip()
        if not title:
            self.send_error_response(400, "标题不能为空")
            return

        order_id = f"WO-{datetime.now(UTC).year}-{len(_load_work_orders()) + 1:03d}"
        new_order = {
            "id": order_id,
            "title": title,
            "location": body.get("location", "待确认"),
            "priority": body.get("priority", "medium"),
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
            "assigned_to": body.get("assigned_to", auth.user.username),
            "description": body.get("description", ""),
        }

        orders = _load_work_orders()
        orders.append(new_order)
        try:
            _save_work_orders(orders)
        except (OSError, TypeError, ValueError) as exc:
            logger.error("工单保存失败: %s", exc)
            self.send_error_response(503, "工单保存失败，请检查存储权限或磁盘空间")
            return

        self.send_json_response(201, {"order": new_order})


class WorkOrdersUpdateHandler(BaseHandler):
    """PUT /api/v1/work-orders/<id> - Update work order."""

    def do_PUT(self) -> None:
        # Parse ID from path: /api/v1/work-orders/WO-2026-001
        parts = self.path.strip("/").split("/")
        if len(parts) != 3 or parts[2] == "":
            self.send_error_response(404, "Not found")
            return

        order_id = parts[2]
        auth = self._authenticate()
        if not auth:
            return

        body = self._parse_json_body()
        orders = _load_work_orders()
        found = False
        for i, o in enumerate(orders):
            if o.get("id") == order_id:
                for key in ("status", "priority", "assigned_to", "description"):
                    if key in body:
                        orders[i][key] = body[key]
                orders[i]["updated_at"] = datetime.now(UTC).isoformat()
                found = True
                break

        if not found:
            self.send_error_response(404, "工单不存在")
            return

        try:
            _save_work_orders(orders)
        except (OSError, TypeError, ValueError) as exc:
            logger.error("工单保存失败: %s", exc)
            self.send_error_response(503, "工单保存失败，请检查存储权限或磁盘空间")
            return
        self.send_json_response(200, {"order": orders[[o["id"] for o in orders].index(order_id)]})


# ── Inspection Points handlers ───────────────────────────────────────────────

INSPECTION_POINTS_FILE = os.environ.get(
    "M20_INSPECTION_POINTS",
    str(Path(__file__).parent.parent.parent / "var" / "inspection_points.json"),
)


def _load_inspection_points() -> list[dict[str, Any]]:
    try:
        with open(INSPECTION_POINTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_inspection_points(points: list[dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(INSPECTION_POINTS_FILE), exist_ok=True)
    with open(INSPECTION_POINTS_FILE, "w", encoding="utf-8") as f:
        json.dump(points, f, ensure_ascii=False, indent=2)


def _init_default_inspection_points() -> None:
    """Initialize with default inspection points if file doesn't exist."""
    if os.path.exists(INSPECTION_POINTS_FILE):
        return
    # No default inspection points - site-specific configuration required
    _save_inspection_points([])


class InspectionPointsHandler(BaseHandler):
    """GET /api/v1/inspection-points - List inspection points."""

    def do_GET(self) -> None:
        if not self.path.startswith("/api/v1/inspection-points"):
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth and (not self.auth_middleware or not self.auth_middleware.allow_anonymous):
            return

        _init_default_inspection_points()
        points = _load_inspection_points()

        # Filter by area if ?area=xxx
        query = self.path.split("?")[1] if "?" in self.path else ""
        if "area=" in query:
            area = query.split("area=")[1].split("&")[0]
            points = [p for p in points if p.get("area") == area]

        self.send_json_response(200, {"points": points, "total": len(points)})


# ── Timeline / Patrol History handlers ───────────────────────────────────────

TIMELINE_FILE = os.environ.get(
    "M20_TIMELINE_DB",
    str(Path(__file__).parent.parent.parent / "var" / "patrol_timeline.json"),
)


def _load_timeline() -> list[dict[str, Any]]:
    try:
        with open(TIMELINE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_timeline(entries: list[dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(TIMELINE_FILE), exist_ok=True)
    with open(TIMELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def _init_default_timeline() -> None:
    """Initialize with default timeline if file doesn't exist."""
    if os.path.exists(TIMELINE_FILE):
        return
    # No default timeline - wait for real patrol data
    _save_timeline([])


class TimelineHandler(BaseHandler):
    """GET /api/v1/timeline - Get patrol timeline."""

    def do_GET(self) -> None:
        if not self.path.startswith("/api/v1/timeline"):
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth and (not self.auth_middleware or not self.auth_middleware.allow_anonymous):
            return

        _init_default_timeline()
        entries = _load_timeline()

        # Filter by type if ?type=alert or ?type=info
        query = self.path.split("?")[1] if "?" in self.path else ""
        if "type=" in query:
            etype = query.split("type=")[1].split("&")[0]
            entries = [e for e in entries if e.get("type") == etype]

        self.send_json_response(200, {"entries": entries, "total": len(entries)})


# ── User management handlers ─────────────────────────────────────────────────

class UserListHandler(BaseHandler):
    """GET /api/v1/users - List users (admin only)."""

    def do_GET(self) -> None:
        if self.path != "/api/v1/users":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth:
            return
        if auth.role != "admin":
            self.send_error_response(403, "需要管理员权限")
            return

        # Return non-sensitive user info
        conn = sqlite3.connect(self.user_store.path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, username, role, enabled, created_at FROM users").fetchall()
        conn.close()

        users = [
            {
                "id": int(r["id"]),
                "username": r["username"],
                "role": r["role"],
                "enabled": bool(r["enabled"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]
        self.send_json_response(200, {"users": users})


class UserChangePasswordHandler(BaseHandler):
    """POST /api/v1/users/password - Change password."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/users/password":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth:
            return

        body = self._parse_json_body()
        old_password = body.get("old_password", "")
        new_password = body.get("new_password", "")

        if not old_password or not new_password:
            self.send_error_response(400, "请填写旧密码和新密码")
            return

        if len(new_password) < 6:
            self.send_error_response(400, "新密码至少6个字符")
            return

        try:
            # Re-authenticate with old password
            user = self.user_store.authenticate(auth.user.username, old_password)
            # Create new hash
            salt = secrets.token_bytes(16)
            digest = hashlib.pbkdf2_hmac("sha256", new_password.encode("utf-8"), salt, 240000)
            new_hash = "$".join(("pbkdf2_sha256", "240000", salt.hex(), digest.hex()))

            conn = sqlite3.connect(str(self.user_store.path))
            conn.execute(
                "UPDATE users SET password_hash=? WHERE username=?",
                (new_hash, auth.user.username),
            )
            conn.commit()
            conn.close()

            # Revoke all existing sessions
            self.user_store.revoke_session(auth.session.token)

            self.send_json_response(200, {"message": "密码修改成功，请重新登录"})
        except AuthenticationError:
            self.send_error_response(401, "旧密码不正确")
        except Exception as exc:
            logger.error("Password change error: %s", exc)
            self.send_error_response(500, "密码修改失败")


# ── System Info handler ──────────────────────────────────────────────────────

class SystemInfoHandler(BaseHandler):
    """GET /api/v1/system/info - System information."""

    def do_GET(self) -> None:
        if self.path != "/api/v1/system/info":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth and (not self.auth_middleware or not self.auth_middleware.allow_anonymous):
            self.send_error_response(403, "Authentication required")
            return

        # Check control enabled status
        control_enabled = False
        read_only = True
        if self.telemetry_adapter:
            control_enabled = getattr(self.telemetry_adapter, 'control_enabled', False)
            read_only = not control_enabled

        info = {
            "service": "M20 Pro 巡逻机器人监控系统",
            "version": "1.0.0",
            "site": "中升之星奔驰",
            "mode": self.config.runtime_mode if self.config else "unknown",
            "read_only": read_only,
            "control_enabled": control_enabled,
            "auth_enabled": self.config.auth_enabled if self.config else True,
            "hos": {
                "aos_host": self.config.aos_host if self.config else "",
                "aos_port": self.config.aos_port if self.config else 30001,
                "nos_host": self.config.nos_host if self.config else "not_configured",
                "gos_host": self.config.gos_host if self.config else "not_configured",
            },
            "gimbal_connected": (
                bool(self.gimbal_adapter and self.gimbal_adapter.connected)
                if self.gimbal_adapter else False
            ),
            "uptime_seconds": 0,
        }
        self.send_json_response(200, info)


# ── Gimbal Control handlers (read-only aware) ───────────────────────────────

class GimbalStateHandler(BaseHandler):
    """GET /api/v1/gimbal/state"""

    def do_GET(self) -> None:
        if self.path != "/api/v1/gimbal/state":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth and (not self.auth_middleware or not self.auth_middleware.allow_anonymous):
            return

        gimbal = self.gimbal_adapter
        if not gimbal or not getattr(gimbal, "connected", False):
            self.send_json_response(200, {
                "connected": False,
                "message": "云台未连接或地址未配置",
                "pan": 0, "tilt": 0, "zoom": 1.0,
            })
            return

        try:
            state = gimbal.get_state()
            self.send_json_response(200, state)
        except Exception as exc:
            logger.error("Gimbal state error: %s", exc)
            self.send_json_response(200, {"connected": True, "error": str(exc)})


class GimbalMoveHandler(BaseHandler):
    """POST /api/v1/gimbal/move - Requires admin auth, read-only blocks."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/gimbal/move":
            self.send_error_response(404, "Not found")
            return

        # Safety first: block in read-only mode before any other checks
        if self.config and self.config.read_only_mode:
            self.send_json_response(200, {
                "status": "blocked",
                "message": "只读模式：云台移动已禁用",
            })
            return

        auth = self._authenticate()
        if not auth:
            return
        if auth.role != "admin":
            self.send_error_response(403, "需要管理员权限")
            return

        gimbal = self.gimbal_adapter
        if not gimbal or not getattr(gimbal, "connected", False):
            self.send_error_response(503, "云台未连接")
            return

        body = self._parse_json_body()
        direction = body.get("direction", "stop")
        speed = body.get("speed", 5)

        try:
            if gimbal.move_direction(direction, speed):
                self.send_json_response(200, {"status": "ok", "direction": direction, "speed": speed})
            else:
                self.send_error_response(500, "云台控制失败")
        except Exception as exc:
            self.send_error_response(500, str(exc))


class GimbalScanHandler(BaseHandler):
    """GET /api/v1/gimbal/scan - Scan for gimbal on network."""

    def do_GET(self) -> None:
        if not self.path.startswith("/api/v1/gimbal/scan"):
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth and (not self.auth_middleware or not self.auth_middleware.allow_anonymous):
            return

        # Return configured/known gimbal addresses
        result = {
            "configured_host": self.config.gimbal_host if self.config else "",
            "scanning": False,
            "found": [],
            "message": "云台扫描需在局域网内执行，当前仅返回已配置地址",
        }
        self.send_json_response(200, result)


class GimbalDeviceInfoHandler(BaseHandler):
    """GET /api/v1/gimbal/device/info"""

    def do_GET(self) -> None:
        if self.path != "/api/v1/gimbal/device/info":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth and (not self.auth_middleware or not self.auth_middleware.allow_anonymous):
            return

        gimbal = self.gimbal_adapter
        if not gimbal or not getattr(gimbal, "connected", False):
            self.send_json_response(200, {"connected": False, "model": "SR-UPA810T609", "status": "unconnected"})
            return

        try:
            info = gimbal.get_device_info()
            self.send_json_response(200, info)
        except Exception as exc:
            self.send_json_response(200, {"connected": True, "error": str(exc)})


class GimbalZoomHandler(BaseHandler):
    """POST /api/v1/gimbal/zoom"""

    def do_POST(self) -> None:
        if self.path != "/api/v1/gimbal/zoom":
            self.send_error_response(404, "Not found")
            return

        # Safety first: block in read-only mode before any other checks
        if self.config and self.config.read_only_mode:
            self.send_json_response(200, {"status": "blocked", "message": "只读模式：云台变焦已禁用"})
            return

        auth = self._authenticate()
        if not auth:
            return
        if auth.role != "admin":
            self.send_error_response(403, "需要管理员权限")
            return

        gimbal = self.gimbal_adapter
        if not gimbal or not getattr(gimbal, "connected", False):
            self.send_error_response(503, "云台未连接")
            return

        body = self._parse_json_body()
        level = body.get("level", 1.0)
        try:
            if gimbal.zoom_to(level):
                self.send_json_response(200, {"status": "ok", "zoom": level})
            else:
                self.send_error_response(500, "变焦失败")
        except Exception as exc:
            self.send_error_response(500, str(exc))


class GimbalAngleHandler(BaseHandler):
    """POST /api/v1/gimbal/angle"""

    def do_POST(self) -> None:
        if self.path != "/api/v1/gimbal/angle":
            self.send_error_response(404, "Not found")
            return

        # Safety first: block in read-only mode before any other checks
        if self.config and self.config.read_only_mode:
            self.send_json_response(200, {"status": "blocked", "message": "只读模式：云台角度控制已禁用"})
            return

        auth = self._authenticate()
        if not auth:
            return
        if auth.role != "admin":
            self.send_error_response(403, "需要管理员权限")
            return

        if self.config and self.config.read_only_mode:
            self.send_json_response(200, {"status": "blocked", "message": "只读模式：云台控制已禁用"})
            return

        gimbal = self.gimbal_adapter
        if not gimbal or not getattr(gimbal, "connected", False):
            self.send_error_response(503, "云台未连接")
            return

        body = self._parse_json_body()
        pan = body.get("pan", 0)
        tilt = body.get("tilt", 0)
        try:
            if gimbal.set_angle(pan, tilt):
                self.send_json_response(200, {"status": "ok", "pan": pan, "tilt": tilt})
            else:
                self.send_error_response(500, "角度控制失败")
        except Exception as exc:
            self.send_error_response(500, str(exc))


class GimbalVideoHandler(BaseHandler):
    """GET /api/v1/gimbal/video - Get gimbal video URL."""

    def do_GET(self) -> None:
        if self.path != "/api/v1/gimbal/video":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth and (not self.auth_middleware or not self.auth_middleware.allow_anonymous):
            return

        gimbal = self.gimbal_adapter
        if not gimbal or not getattr(gimbal, "connected", False):
            self.send_json_response(200, {
                "connected": False,
                "rtsp_url": "",
                "message": "云台未连接，视频流不可用",
            })
            return

        try:
            urls = gimbal.get_video_urls()
            self.send_json_response(200, {"connected": True, "video_urls": urls})
        except Exception as exc:
            self.send_json_response(200, {"connected": True, "error": str(exc)})


class GimbalConnectHandler(BaseHandler):
    """POST /api/v1/gimbal/connect - Connect to gimbal by IP."""

    def do_POST(self) -> None:
        if self.config and (self.config.read_only_mode or not self.config.control_enabled):
            self.send_error_response(403, "控制未启用")
            return

        if self.path != "/api/v1/gimbal/connect":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth:
            return

        if auth.role != "admin":
            self.send_error_response(403, "admin role required")
            return

        body = self._parse_json_body()
        host = body.get("host", "").strip()
        username = body.get("username", "admin")
        password = body.get("password", "123456")

        if not host:
            self.send_error_response(400, "host 不能为空")
            return

        # Validate IP format
        try:
            ipaddress.ip_address(host)
        except ValueError:
            self.send_error_response(400, "IP 地址格式错误")
            return

        # Update server's gimbal adapter
        port = body.get("port", 80)
        if type(port) is not int or not 1 <= port <= 65535:
            self.send_error_response(400, "端口必须是 1-65535 的整数")
            return
        new_config = GimbalConfig(
            host=host,
            port=port,
            username=username,
            password=password,
        )

        # Create new adapter and try to connect
        new_adapter = SoarGimbalAdapter(new_config)
        if new_adapter.auto_connect():
            # Close old adapter if exists
            if self.server_instance and self.server_instance.gimbal_adapter:
                try:
                    self.server_instance.gimbal_adapter.close()
                except Exception:
                    pass
            
            # Update server's gimbal adapter reference
            self.server_instance.gimbal_adapter = new_adapter
            self.server_instance.gimbal_connected = True
            self.server_instance.gimbal_host = host
            logger.info("云台手动连接成功: %s", host)

            # Update video stream manager with gimbal RTSP URLs
            if self.server_instance and self.server_instance.video_manager:
                video_urls = new_adapter.get_video_urls()
                if video_urls.get("visible_light"):
                    self.server_instance.video_manager.set_rtsp_url("front", video_urls["visible_light"])
                if video_urls.get("thermal"):
                    self.server_instance.video_manager.set_rtsp_url("thermal", video_urls["thermal"])

            self.send_json_response(200, {
                "success": True,
                "host": host,
                "message": "云台连接成功",
                "video_urls": video_urls,
            })
        else:
            logger.warning("云台连接失败: %s", host)
            try:
                new_adapter.close()
            except Exception:
                pass
            self.send_error_response(503, f"云台连接失败: {host}，请检查 IP 和凭据")
