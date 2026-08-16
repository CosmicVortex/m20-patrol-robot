"""API route handlers for M20 Web service.

Provides HTTP handlers for auth, status, devices, and navigation endpoints.
"""

from __future__ import annotations

import json
import logging
import subprocess
import select
import time

import ipaddress
from urllib.parse import urlparse
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from datetime import UTC
except ImportError:  # Python 3.8
    UTC = timezone.utc

from backend.app.auth.middleware import AuthMiddleware, AuthRequiredError, AuthResult
from backend.app.auth.store import AuthUser, AuthenticationError, Session, UserStore
from backend.app.api.response import ApiFormatter, RequestContext
from backend.app.api.base_handler import BaseHandler
from backend.app.robot.telemetry import TelemetryAdapter
from backend.app.navigation.service import NavigationService
from backend.app.config import WebServiceConfig
from backend.app.protocol.messages import PatrolMessage

logger = logging.getLogger(__name__)


class HealthHandler(BaseHandler):
    """GET /api/v1/health - Service health check."""

    def do_GET(self) -> None:
        if self.path == "/api/v1/health":
            payload = self.telemetry_adapter.get_status_payload() if self.telemetry_adapter else {}
            health = {
                "service": "m20-patrol-web",
                "runtime_mode": getattr(self.telemetry_adapter.config, "runtime_mode", "unconfigured") if self.telemetry_adapter else "unconfigured",
                "read_only_mode": not getattr(self.telemetry_adapter, "control_enabled", False),
                "control_enabled": getattr(self.telemetry_adapter, "control_enabled", False),
                "telemetry_tx_enabled": self.config.telemetry_tx_enabled if self.config else False,
                "source": payload.get("source", "NO_DATA"),
                "connected": payload.get("connected", False),
                "valid_frames": payload.get("valid_frames", 0),
                "bytes_received": payload.get("bytes_received", 0),
                "network_ready": payload.get("network_ready", False),
                "tcp_connected": payload.get("tcp_connected", False),
                "frame_valid": payload.get("frame_valid", False),
                "message_parsed": payload.get("message_parsed", False),
                "status_accepted": payload.get("status_accepted", False),
                "telemetry_fresh": payload.get("telemetry_fresh", False),
                "data_state": "REAL_FRESH" if payload.get("telemetry_fresh") else payload.get("source", "NO_DATA"),
                "age_ms": payload.get("age_ms"),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            stale_limit = self.telemetry_adapter.config.stale_after_s * 1000 if self.telemetry_adapter else 0
            # 支持两种健康模式：实时只读模式 或 完整控制模式
            is_readonly_mode = self.config.runtime_mode == "realtime_readonly" if self.config else False
            is_control_mode = self.config.control_enabled if self.config else False
            health["healthy"] = (
                (is_readonly_mode or is_control_mode)
                and health["source"] == "REAL"
                and health["connected"] is True
                and health["valid_frames"] > 0
                and health["bytes_received"] > 0
                and health["telemetry_fresh"] is True
                and isinstance(health["age_ms"], (int, float))
                and 0 <= health["age_ms"] < stale_limit
            )
            self.send_raw_json_response(200 if health["healthy"] else 503, health)
        else:
            self.send_error_response(404, "Not found")


class AuthLoginHandler(BaseHandler):
    """POST /api/v1/auth/login - User login."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/auth/login":
            self.send_error_response(404, "Not found")
            return

        body = self._parse_json_body()
        username = body.get("username", "").strip()
        password = body.get("password", "")

        if not username or not password:
            self.send_error_response(400, "username and password are required")
            return

        try:
            user = self.user_store.authenticate(username, password)
            session = self.user_store.create_session(user)
            logger.info("用户登录: %s", user.username)
            body = {
                "user_id": user.user_id,
                "username": user.username,
                "role": user.role,
                "session_expires": session.expires_at,
            }
            encoded = json.dumps(ApiFormatter.success(body), ensure_ascii=False).encode("utf-8")
            if self.auth_middleware is None:
                self.send_error_response(500, "authentication middleware unavailable")
                return
            self.send_response(200)
            self.auth_middleware.set_session_cookie(self, session)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(encoded)
        except AuthenticationError:
            logger.warning("登录失败")
            self.send_error_response(401, "invalid credentials")
        except Exception as exc:
            logger.error("Login error: %s", exc)
            self.send_error_response(500, "internal server error")


class AuthLogoutHandler(BaseHandler):
    """POST /api/v1/auth/logout - User logout."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/auth/logout":
            self.send_error_response(404, "Not found")
            return

        token = self.auth_middleware._extract_token(self) if self.auth_middleware else None
        if token and self.user_store:
            self.user_store.revoke_session(token)
        encoded = json.dumps(
            ApiFormatter.success({"status": "logged_out"}), ensure_ascii=False
        ).encode("utf-8")
        self.send_response(200)
        if self.auth_middleware:
            self.auth_middleware.revoke_session_cookie(self)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(encoded)


class AuthMeHandler(BaseHandler):
    """GET /api/v1/auth/me - Current user info."""

    def do_GET(self) -> None:
        if self.path != "/api/v1/auth/me":
            self.send_error_response(404, "Not found")
            return

        # 已取消登录流程，直接返回admin用户信息
        self.send_json_response(200, {
            "user_id": 1,
            "username": "admin",
            "role": "admin",
        })


class StatusLatestHandler(BaseHandler):
    """GET /api/v1/status/latest - Latest robot status."""

    def do_GET(self) -> None:
        if self.path != "/api/v1/status/latest":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth and (not self.auth_middleware or not self.auth_middleware.allow_anonymous):
            return

        if self.telemetry_adapter is None:
            self.send_error_response(503, "Telemetry adapter not configured")
            return

        try:
            payload = self.telemetry_adapter.get_status_payload()
            # Keep the status endpoint machine-readable and compatible with
            # the deployment health gate. Auth/login responses are wrapped,
            # telemetry status is intentionally returned as the raw snapshot.
            self.send_raw_json_response(200, payload)
        except Exception as exc:
            logger.error("Status fetch error: %s", exc)
            self.send_error_response(500, str(exc))


class DevicesListHandler(BaseHandler):
    """GET /api/v1/devices - List connected devices."""

    def do_GET(self) -> None:
        if self.path != "/api/v1/devices":
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth and (not self.auth_middleware or not self.auth_middleware.allow_anonymous):
            return

        self.send_json_response(200, {
            "devices": [
                {"id": "aos", "type": "application_server", "host": (self.config.aos_host if self.config else "not_configured") or "not_configured", "status": "configured"},
                {"id": "gos", "type": "guard_operator_station", "host": (self.config.host if self.config else "127.0.0.1"), "status": "configured"},
                {"id": "nos", "type": "navigation_operator_station", "host": (self.config.nos_host if self.config and self.config.nos_host else "not_configured"), "status": "configured"},
            ]
        })


class NavigationStatusHandler(BaseHandler):
    """GET /api/v1/navigation/status - Navigation task status."""

    def do_GET(self) -> None:
        if not self.path.startswith("/api/v1/navigation/status"):
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth and (not self.auth_middleware or not self.auth_middleware.allow_anonymous):
            return

        nav_service = self.nav_service
        if nav_service is None:
            self.send_error_response(503, "Navigation service not configured")
            return

        status = nav_service.get_status()
        self.send_json_response(200, status)


class NavigationAuthorizeHandler(BaseHandler):
    """POST /api/v1/navigation/authorize - Request navigation control authorization."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/navigation/authorize":
            self.send_error_response(404, "Not found")
            return

        # Safety first: block in read-only mode before any other checks
        if self.config and self.config.read_only_mode:
            self.send_json_response(200, {
                "status": "blocked",
                "message": "只读模式：导航授权已禁用",
            })
            return

        auth = self._authenticate()
        if not auth:
            return

        if auth.role != "admin":
            self.send_error_response(403, "admin role required")
            return

        nav_service = self.nav_service
        if nav_service is None:
            self.send_error_response(503, "Navigation service not configured")
            return

        body = self._parse_json_body()
        operator = body.get("operator", auth.user.username)
        note = body.get("note", "")

        try:
            result = nav_service.authorize(operator, note)
            self.send_json_response(200, result)
        except Exception as exc:
            logger.error("Authorization error: %s", exc)
            self.send_error_response(500, str(exc))


class NavigationDeauthorizeHandler(BaseHandler):
    """POST /api/v1/navigation/deauthorize - Revoke navigation authorization."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/navigation/deauthorize":
            self.send_error_response(404, "Not found")
            return
        if self.config and self.config.read_only_mode:
            self.send_json_response(200, {"status": "blocked", "message": "只读模式：导航撤销已禁用"})
            return
        auth = self._authenticate()
        if not auth:
            return
        if auth.role != "admin":
            self.send_error_response(403, "admin role required")
            return
        if self.nav_service is None:
            self.send_error_response(503, "Navigation service not configured")
            return
        self.send_json_response(200, self.nav_service.deauthorize())


class NavigationTaskHandler(BaseHandler):
    """POST /api/v1/navigation/tasks - Submit navigation task."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/navigation/tasks":
            self.send_error_response(404, "Not found")
            return

        # Safety first: block in read-only mode before any other checks
        if self.config and self.config.read_only_mode:
            self.send_json_response(200, {
                "status": "blocked",
                "message": "只读模式：导航控制已禁用",
            })
            return

        auth = self._authenticate()
        if not auth:
            return

        if auth.role != "admin":
            self.send_error_response(403, "admin role required")
            return

        nav_service = self.nav_service
        if nav_service is None:
            self.send_error_response(503, "Navigation service not configured")
            return

        body = self._parse_json_body()
        action = body.get("action")

        if action == "cancel":
            try:
                result = nav_service.cancel_navigation()
                self.send_json_response(200, result)
            except Exception as exc:
                logger.error("Cancel navigation error: %s", exc)
                self.send_error_response(500, str(exc))
        else:
            # Send navigation command
            pos_x = body.get("pos_x", 0.0)
            pos_y = body.get("pos_y", 0.0)
            pos_z = body.get("pos_z", 0.0)
            angle_yaw = body.get("angle_yaw", 0.0)
            map_id = body.get("map_id", 0)  # 官方协议默认值0，与service.py保持一致

            try:
                result = nav_service.send_navigation(pos_x, pos_y, pos_z, angle_yaw, map_id)
                self.send_json_response(200, result)
            except Exception as exc:
                logger.error("Navigation error: %s", exc)
                self.send_error_response(500, str(exc))


class NavigationCancelHandler(BaseHandler):
    """POST /api/v1/navigation/cancel - Cancel navigation task."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/navigation/cancel":
            self.send_error_response(404, "Not found")
            return

        # Safety first: block in read-only mode before any other checks
        if self.config and self.config.read_only_mode:
            self.send_json_response(200, {
                "status": "blocked",
                "message": "只读模式：导航取消已禁用",
            })
            return

        auth = self._authenticate()
        if not auth:
            return

        if auth.role != "admin":
            self.send_error_response(403, "admin role required")
            return

        nav_service = self.nav_service
        if nav_service is None:
            self.send_error_response(503, "Navigation service not configured")
            return

        try:
            result = nav_service.cancel_navigation()
            self.send_json_response(200, result)
        except Exception as exc:
            logger.error("Cancel navigation error: %s", exc)
            self.send_error_response(500, str(exc))


class EmergencyStopHandler(BaseHandler):
    """POST /api/v1/emergency/stop - Emergency stop (requires admin auth)."""

    def do_POST(self) -> None:
        if self.path != "/api/v1/emergency/stop":
            self.send_error_response(404, "Not found")
            return

        # Safety first: block in read-only mode before any other checks
        if self.config and self.config.read_only_mode:
            self.send_json_response(200, {
                "authorized": False,
                "message": "紧急停止已禁用：只读模式",
            })
            return

        auth = self._authenticate()
        if not auth:
            return

        if auth.role != "admin":
            self.send_error_response(403, "需要管理员权限")
            return

        nav_service = self.nav_service
        if nav_service is None:
            self.send_error_response(503, "Navigation service not configured")
            return

        result = nav_service.get_status()
        if not result.get("authorized"):
            self.send_json_response(200, {
                "authorized": False,
                "message": "需要现场授权才能执行紧急停止",
                "service_status": result,
            })
            return

        if not result.get("control_enabled"):
            self.send_json_response(200, {
                "authorized": False,
                "message": "控制未启用：紧急停止已禁用",
            })
            return

        # Send soft emergency stop command to robot FIRST (critical path)
        cmd_ok = False
        cmd_error = ""
        try:
            service = getattr(self.server_instance, 'motion_service', None)
            if service and hasattr(service, '_client'):
                msg = PatrolMessage(
                    message_type=2,
                    command=22,
                    sent_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                    items={"MotionParam": 2},  # MOTION_STATE_SOFT_ESTOP
                )
                service._client.send_control(msg)
                cmd_ok = True
                logger.info("紧急停止指令已发送到机器人")
            else:
                cmd_error = "运动控制服务不可用"
                logger.error(cmd_error)
        except Exception as e:
            cmd_error = str(e)
            logger.error("紧急停止指令发送失败: %s", e)

        # Return response AFTER command is sent
        self.send_json_response(200, {
            "authorized": True,
            "message": "紧急停止指令已发送" if cmd_ok else f"授权成功但指令发送失败: {cmd_error}",
            "command_sent": cmd_ok,
            "timestamp": datetime.now(UTC).isoformat(),
        })


class VideoStatusHandler(BaseHandler):
    """GET /api/v1/video - Camera stream status."""

    def do_GET(self) -> None:
        if self.path != "/api/v1/video":
            self.send_error_response(404, "Not found")
            return

        # Video metadata contains internal RTSP topology; require a session.
        auth = self._authenticate()
        if not auth:
            return
        allow_real_io = (self.config.allow_real_io if self.config else False)

        # Build status from VideoStreamManager if available
        video_mgr = self.video_manager
        if video_mgr:
            states = video_mgr.get_all_states()
            sources = {}
            for source, state_info in states.items():
                sources[source] = {
                    "state": state_info.get("state", "blocked"),
                    "rtsp_url": state_info.get("rtsp_url", ""),
                    "playback_url": state_info.get("playback_url"),
                    "last_update": state_info.get("last_update"),
                    "label": state_info.get("label", source),
                }
        else:
            sources = {
                "front": {
                    "state": "blocked" if not allow_real_io else "unverified",
                    "rtsp_url": "rtsp://10.21.31.103:8554/video1",
                    "playback_url": None,
                    "label": "前向本体相机",
                    "note": "需现场ffprobe确认可达性",
                },
                "rear": {
                    "state": "blocked" if not allow_real_io else "unverified",
                    "rtsp_url": "rtsp://10.21.31.103:8554/video2",
                    "playback_url": None,
                    "label": "后向本体相机",
                    "note": "需现场ffprobe确认可达性",
                },
                "thermal": {
                    "state": "blocked" if not allow_real_io else "unverified",
                    "rtsp_url": f"rtsp://{self.config.gimbal_host}:554/id=2&type=0" if self.config and self.config.gimbal_host else "",
                    "playback_url": None,
                    "label": "热成像相机",
                    "note": "来自光电吊舱，需确认 gimbal_host 配置",
                },
                "body_front": {
                    "state": "blocked" if not allow_real_io else "unverified",
                    "rtsp_url": "",
                    "playback_url": None,
                    "label": "车身广角前视",
                    "note": "现场配置视频地址后探测",
                },
            }

        self.send_json_response(200, {
            "sources": sources,
            "status": "VIDEO_IO_BLOCKED" if not allow_real_io else "VIDEO_IO_ENABLED",
            "message": "视频流默认禁用，配置 RTSP 地址后启用。" if not allow_real_io else "视频流已启用，等待 ffprobe 探测",
        })


class VideoConfigHandler(BaseHandler):
    """POST /api/v1/video/config - Update RTSP URLs for camera sources."""

    def do_POST(self) -> None:
        if not self.path.startswith("/api/v1/video/config"):
            self.send_error_response(404, "Not found")
            return

        auth = self._authenticate()
        if not auth:
            self.send_error_response(401, "Unauthorized")
            return

        # Only admin can configure video
        if auth.role != "admin":
            self.send_error_response(403, "Admin required")
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_error_response(400, "Invalid JSON")
            return

        video_mgr = self.video_manager
        if video_mgr is None:
            self.send_error_response(503, "Video manager not available")
            return

        if not isinstance(data, dict):
            self.send_error_response(400, "请求体必须是对象")
            return
        sources = data.get('sources', {})
        if not isinstance(sources, dict):
            self.send_error_response(400, "sources 必须是对象")
            return
        results = {}
        known_sources = video_mgr.get_all_states()
        for source, config in sources.items():
            if source not in known_sources:
                results[source] = {'success': False, 'error': '未知视频源'}
                continue
            if not isinstance(config, dict):
                results[source] = {'success': False, 'error': '视频源配置格式错误'}
                continue
            rtsp_url = config.get('rtsp_url', '')
            parsed = None
            valid_url = False
            try:
                parsed = urlparse(rtsp_url) if isinstance(rtsp_url, str) else None
                valid_url = bool(parsed and parsed.scheme == 'rtsp' and parsed.hostname and parsed.path and not parsed.username and not parsed.password)
                if valid_url and parsed is not None and parsed.hostname is not None:
                    if not (1 <= (parsed.port or 554) <= 65535):
                        valid_url = False
                    if parsed.hostname.replace('.', '').isdigit():
                        ipaddress.ip_address(parsed.hostname)
            except (ValueError, TypeError):
                valid_url = False
            if valid_url:
                results[source] = {'success': video_mgr.set_rtsp_url(source, rtsp_url)}
            else:
                results[source] = {'success': False, 'error': 'RTSP 地址格式错误'}

        self.send_json_response(200, {'results': results})


class VideoStreamControlHandler(BaseHandler):
    """POST /api/v1/video/{probe,start,stop} for configured camera sources."""

    def do_POST(self) -> None:
        action = self.path.rsplit('/', 1)[-1]
        if self.path not in {
            '/api/v1/video/probe', '/api/v1/video/start', '/api/v1/video/stop'
        }:
            self.send_error_response(404, "Not found")
            return
        auth = self._authenticate()
        if not auth:
            return
        if auth.role != 'admin':
            self.send_error_response(403, '需要管理员权限')
            return
        if self.video_manager is None:
            self.send_error_response(503, 'Video manager not available')
            return
        body = self._parse_json_body()
        if not isinstance(body, dict):
            self.send_error_response(400, '请求体必须是对象')
            return
        source = body.get('source')
        if not isinstance(source, str) or source not in self.video_manager.get_all_states():
            self.send_error_response(400, '未知视频源')
            return
        operation = {
            'probe': self.video_manager.probe_camera,
            'start': self.video_manager.start_stream,
            'stop': self.video_manager.stop_stream,
        }[action]
        try:
            result = self.video_manager.run_sync(operation, source)
        except Exception as exc:
            logger.error('视频操作失败: %s', exc)
            self.send_error_response(503, '视频操作失败')
            return
        self.send_json_response(200, result)


class VideoPlaybackHandler(BaseHandler):
    """提供浏览器可识别的 fragmented MP4；不依赖 dumped 或媒体服务器。"""

    def do_GET(self) -> None:
        prefix = "/api/v1/video/playback/"
        clean_path = self.path.split("?", 1)[0]
        source = clean_path[len(prefix):] if clean_path.startswith(prefix) else ""
        video_mgr = self.video_manager
        if video_mgr is None or source not in video_mgr.get_all_states():
            self.send_error_response(404, "未知视频源")
            return
        auth = self._authenticate()
        if not auth:
            return
        if not getattr(video_mgr, "allow_real_io", False):
            self.send_error_response(503, "视频 I/O 未启用")
            return
        config = video_mgr.get_camera_config(source)
        if config is None or not config.rtsp_url:
            self.send_error_response(503, "视频源未配置 RTSP 地址")
            return
        try:
            process = subprocess.Popen(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-rw_timeout", "5000000", "-rtsp_transport", "tcp",
                 "-i", config.rtsp_url, "-an", "-c:v", "libx264", "-preset", "ultrafast",
                 "-tune", "zerolatency", "-movflags", "frag_keyframe+empty_moov",
                 "-f", "mp4", "pipe:1"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0,
            )
        except FileNotFoundError:
            self.send_error_response(503, "GOS 主机未安装 ffmpeg，无法提供浏览器视频流")
            return
        except OSError:
            self.send_error_response(503, "无法启动 ffmpeg 视频转码进程")
            return
        video_mgr.register_playback_process(process)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            assert process.stdout is not None
            deadline = time.monotonic() + 15
            while True:
                ready, _, _ = select.select([process.stdout], [], [], 1.0)
                if not ready:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("视频流在规定时间内没有输出")
                    continue
                chunk = process.stdout.read(64 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except TimeoutError as exc:
            logger.warning("浏览器视频流超时: %s", exc)
        except (BrokenPipeError, ConnectionResetError, OSError):
            logger.info("浏览器视频客户端已断开: %s", source)
        finally:
            video_mgr.unregister_playback_process(process)
            if process.stdout is not None:
                try:
                    process.stdout.close()
                except OSError:
                    pass
            if process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=3)
                except (OSError, subprocess.TimeoutExpired):
                    try:
                        process.kill()
                        process.wait(timeout=3)
                    except (OSError, subprocess.TimeoutExpired) as exc:
                        logger.error("视频转码进程无法确认退出: %s", exc)
