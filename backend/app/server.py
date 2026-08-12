"""M20 Web service - main entry point.

Starts the HTTP server with authentication, telemetry, and API routes.
"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import threading
import os
import traceback
import mimetypes
import socket
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional

# Ensure backend is importable
# __file__ = backend/app/server.py
# parent.parent = backend/
# parent.parent.parent = project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.auth.middleware import AuthMiddleware
from backend.app.auth.store import UserStore
from backend.app.config import ConfigLoader, WebServiceConfig
from backend.app.robot.telemetry import TelemetryAdapter, ConnectionConfig
from backend.app.api.router import ApiRouter
from backend.app.api.base_handler import BaseHandler
from backend.app.navigation.service import NavigationService
from backend.app.motion.service import MotionControlService, MotionSafetySnapshot
from backend.app.navigation.v010 import NavigationSafetySnapshot
from backend.app.robot.basic_client import BasicServerConfig
from backend.app.gimbal.adapter import SoarGimbalAdapter, GimbalConfig
from backend.app.robot.basic_client import BasicServerClient
from backend.app.video.stream_manager import VideoStreamManager
from backend.app.websocket import ws_handler
from backend.app.websocket.upgrade import WebSocketUpgradeHandler

logger = logging.getLogger(__name__)


class M20WebServer:
    """M20 patrol robot web service."""

    def __init__(self, config: WebServiceConfig) -> None:
        self.config = config
        self.telemetry_adapter: Optional[TelemetryAdapter] = None
        self.user_store: Optional[UserStore] = None
        self.auth_middleware: Optional[AuthMiddleware] = None
        self.nav_service: Optional[NavigationService] = None
        self.motion_service: Optional[MotionControlService] = None
        self.router: Optional[ApiRouter] = None
        self.server: Optional[ThreadingHTTPServer] = None
        self.video_manager: Optional[VideoStreamManager] = None
        self.ws_upgrade_handler: Optional[WebSocketUpgradeHandler] = None

    def setup(self) -> None:
        """Initialize all components."""
        # Setup authentication store
        db_path = Path(self.config.auth_db_path or (Path(__file__).parent / "data" / "m20_auth.db"))
        self.user_store = UserStore(db_path, session_ttl_s=self.config.session_ttl_s)

        # Never ship a known default password in production. For demo/演示
        # deployments the project owner has confirmed 123456 as the admin
        # default; mark it explicitly so operators know it must be changed
        # before any production handover.
        self._ensure_admin_user()

        # Setup auth middleware
        self.auth_middleware = AuthMiddleware(
            self.user_store,
            allow_anonymous=(not self.config.auth_enabled) or self.config.allow_anonymous,
        )

        # Always create the adapter. In simulated mode it provides an explicit
        # SIMULATED/NO_DATA API state instead of making the endpoint disappear.
        logger.info("初始化遥测适配器...")
        telemetry_config = ConnectionConfig(
            host=self.config.aos_host,
            tcp_port=self.config.aos_port,
            runtime_mode=self.config.runtime_mode,
            read_only=self.config.read_only_mode,
            telemetry_tx_enabled=self.config.telemetry_tx_enabled,
            telemetry_receive_enabled=self.config.telemetry_receive_enabled,
            stale_after_s=self.config.stale_after_s,
        )
        self.telemetry_adapter = TelemetryAdapter(
            telemetry_config,
            control_enabled=self.config.control_enabled,
        )

        # Setup navigation service (disabled by default until authorized)
        basic_config = BasicServerConfig(
            host=self.config.aos_host,
            tcp_port=self.config.aos_port,
            control_enabled=self.config.control_enabled,
            transmit_enabled=self.config.control_enabled,
            stale_after_seconds=self.config.stale_after_s,
        )
        safety_snapshot = NavigationSafetySnapshot(
            field_authorization="",  # 空字符串表示未授权，后续由遥测数据更新
            control_enabled=self.config.control_enabled,
            tcp_connected=False,
            location_normal=False,
            obstacle_avoidance_active=True,
            hard_estop_active=False,
            protective_fault_active=False,
            battery_percent=0,  # 未收到真实电量前按失效安全状态处理
            active_task=False,
        )
        basic_client = BasicServerClient(basic_config)
        self.nav_service = NavigationService(basic_client, safety_snapshot)

        # Setup motion control service (uses same client as navigation)
        motion_safety_snapshot = MotionSafetySnapshot(
            control_enabled=self.config.control_enabled,
            tcp_connected=False,
            hard_estop_active=False,
            protective_fault_active=False,
            battery_percent=0,
            motion_state=0,
        )
        self.motion_service = MotionControlService(basic_client, motion_safety_snapshot)

        # Setup video stream manager
        self.video_manager = VideoStreamManager(allow_real_io=self.config.allow_real_io)

        # Setup gimbal adapter with auto-discovery support (MUST be before router)
        self.gimbal_adapter: Optional[SoarGimbalAdapter] = None
        self.gimbal_connected = False
        self.gimbal_host = ""
        if self.config.gimbal_host:
            logger.info("配置云台地址: %s", self.config.gimbal_host)
            gimbal_config = GimbalConfig(
                host=self.config.gimbal_host,
                username=self.config.gimbal_username,
                password=self.config.gimbal_password,
            )
            self.gimbal_adapter = SoarGimbalAdapter(gimbal_config)
            # 在后台线程中执行云台连接/扫描，避免阻塞 HTTP 服务启动
            def _gimbal_init() -> None:
                if self.gimbal_adapter and self.gimbal_adapter.auto_connect():
                    logger.info("云台已连接: %s", self.config.gimbal_host)
                    self.gimbal_connected = True
                else:
                    logger.warning("云台连接失败，可使用 /api/v1/gimbal/scan 扫描")
            threading.Thread(target=_gimbal_init, daemon=True, name="gimbal-init").start()
        else:
            # No host configured, enable auto-discovery mode
            logger.info("云台地址未配置，支持自动发现 (/api/v1/gimbal/scan)")
            self.gimbal_adapter = SoarGimbalAdapter()

        # Setup API router
        self.router = ApiRouter(
            user_store=self.user_store,
            auth_middleware=self.auth_middleware,
            telemetry_adapter=self.telemetry_adapter,
            nav_service=self.nav_service,
            config=self.config,
            gimbal_adapter=self.gimbal_adapter,
            video_manager=self.video_manager,
            server_instance=self,  # Inject server reference for handlers
            motion_service=self.motion_service,
        )

        # Initialize WebSocket handlers
        if self.video_manager and self.nav_service:
            ws_handler.init_ws_handlers(self.video_manager, self.nav_service)
            self.ws_upgrade_handler = WebSocketUpgradeHandler(
                video_handler=ws_handler.video_ws_handler,
                nav_handler=ws_handler.navigation_ws_handler,
                auth_middleware=self.auth_middleware,
            )
            logger.info("WebSocket handlers initialized")
        else:
            logger.warning("WebSocket handlers not initialized (missing video_manager or nav_service)")

    def _ensure_admin_user(self) -> None:
        """Create default admin user if not exists."""
        if self.user_store is None:
            return
        password = os.environ.get("M20_ADMIN_PASSWORD")
        if not password:
            # 使用文档规定的固定密码
            password = "123456"
            logger.info("使用文档默认管理员密码，请首次登录后修改")
        try:
            self.user_store.authenticate("admin", password)
        except Exception:
            try:
                admin = self.user_store.create_user("admin", password, "admin")
                logger.info("Provisioned administrator account: %s", admin.username)
            except Exception as exc:
                logger.warning("Failed to provision administrator: %s", exc)

    def _register_safety_callbacks(self) -> None:
        """Synchronize transport and fail-safe telemetry into control services."""
        if self.telemetry_adapter and self.nav_service:
            nav_service = self.nav_service

            def _sync_nav(payload: dict[str, Any]) -> None:
                safety_data = dict(payload.get("data", {}))
                safety_data["tcp_connected"] = payload.get("tcp_connected", False)
                safety_data["battery_percent"] = payload.get("battery_percent", 0)
                nav_service.update_safety_from_telemetry(safety_data)

            self.telemetry_adapter.set_navigation_sync_callback(_sync_nav)

        if self.telemetry_adapter and self.motion_service:
            motion_service = self.motion_service

            def _sync_motion(payload: dict[str, Any]) -> None:
                safety_data = dict(payload.get("data", {}))
                safety_data["tcp_connected"] = payload.get("tcp_connected", False)
                safety_data["battery_percent"] = payload.get("battery_percent", 0)
                motion_service.update_safety(safety_data)

            self.telemetry_adapter.set_motion_sync_callback(_sync_motion)

        if self.telemetry_adapter and self.nav_service and self.motion_service:
            def _sync_client(client: BasicServerClient) -> None:
                nav_service = self.nav_service
                motion_service = self.motion_service
                if nav_service is not None:
                    nav_service._client = client
                if motion_service is not None:
                    motion_service._client = client
            self.telemetry_adapter.set_client_callback(_sync_client)

    def start(self) -> None:
        """Start the web server."""
        logger.info("=" * 60)
        logger.info("开始启动 M20 Web 服务...")
        logger.info("=" * 60)
        self.setup()
        logger.info("组件初始化完成，准备绑定端口...")

        self._register_safety_callbacks()

        if self.telemetry_adapter:
            self.telemetry_adapter.start()

        # Setup request handler
        handler = self._create_handler()

        # Start HTTP server
        logger.info("尝试绑定 %s:%s...", self.config.host, self.config.port)
        try:
            self.server = ThreadingHTTPServer(
                (self.config.host, self.config.port),
                handler,
            )
            logger.info("✓ 端口绑定成功: %s:%s", self.config.host, self.config.port)
        except OSError as e:
            logger.error("✗ 无法绑定到 %s:%s - %s", self.config.host, self.config.port, e)
            logger.info("尝试使用其他端口...")
            # 尝试其他端口
            for alt_port in range(self.config.port + 1, self.config.port + 11):
                try:
                    self.server = ThreadingHTTPServer(
                        (self.config.host, alt_port),
                        handler,
                    )
                    self.config = replace(self.config, port=alt_port)
                    logger.info("✓ 使用备用端口: %s", alt_port)
                    break
                except OSError as e2:
                    logger.warning("端口 %s 也被占用: %s", alt_port, e2)
                    continue
            else:
                logger.error("✗ 无法绑定到任何端口（8080-8090）")
                raise RuntimeError("无法绑定到任何端口")

        logger.info("")
        logger.info("M20 Web Service 已启动")
        logger.info("  地址: http://%s:%s", self.config.host, self.config.port)
        logger.info("  运行模式: %s", self.config.runtime_mode)
        logger.info("  只读模式: %s", self.config.read_only_mode)
        logger.info("  控制启用: %s", self.config.control_enabled)
        logger.info("  认证启用: %s", self.config.auth_enabled)
        logger.info("  云台地址: %s", self.config.gimbal_host or "未配置")
        logger.info("")
        logger.info("遥测目标: %s:%s (模式: %s)", self.config.aos_host, self.config.aos_port, self.config.runtime_mode)
        logger.info("安全配置: 只读模式=%s, 控制命令=%s", self.config.read_only_mode, self.config.control_enabled)
        logger.info("=" * 60)

        # 设置信号处理器
        self._setup_signal_handlers()

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在关闭...")
        except Exception as e:
            logger.error("服务运行异常: %s", e)
            traceback.print_exc()
        finally:
            self.stop()

    def _setup_signal_handlers(self) -> None:
        """设置信号处理器以确保优雅关闭。"""
        def handle_signal(signum, frame) -> None:
            signal_name = signal.Signals(signum).name
            logger.info("收到信号 %s，正在关闭服务...", signal_name)
            self.stop()

        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)

    def _create_handler(self) -> type[BaseHTTPRequestHandler]:
        """Create request handler class with injected dependencies."""
        config = self.config
        router = self.router
        server_instance = self

        class M20RequestHandler(BaseHandler):
            def log_message(self, format: str, *args: object) -> None:
                logger.info("%s %s - %s", self.command, self.path, format % args)

            def finish(self) -> None:
                if getattr(self, "_ws_handoff", False):
                    # The WebSocket handler owns the underlying socket now.
                    # Close only the buffered I/O wrappers so the HTTP server
                    # does not also close the raw socket.
                    if not self.wfile.closed:
                        try:
                            self.wfile.flush()
                        except OSError:
                            pass
                        self.wfile.close()
                    if not self.rfile.closed:
                        self.rfile.close()
                    return
                super().finish()

            def do_GET(self) -> None:
                self._handle_request()

            def do_POST(self) -> None:
                self._handle_request()

            def do_PUT(self) -> None:
                self._handle_request()

            def do_DELETE(self) -> None:
                self._handle_request()

            def _handle_request(self) -> None:
                request_path = self.path.split("?", 1)[0]
                # Decode URL encoding to prevent bypass
                from urllib.parse import unquote
                request_path = unquote(request_path)
                if request_path == "/":
                    request_path = "/index.html"
                if not request_path.startswith("/api/") and not request_path.startswith("/ws/"):
                    # Resolve static_root safely (Python 3.8 compatible)
                    static_root = Path(config.static_root)
                    if not static_root.is_absolute():
                        # Get project root from this file's location
                        project_root = Path(__file__).parent.parent.parent
                        static_root = project_root / static_root
                    # Use absolute path - avoid resolve() on Python 3.8
                    root = static_root.absolute().resolve()
                    asset = (root / request_path.lstrip("/")).resolve()
                    # Security check: ensure asset is within root directory
                    try:
                        asset.relative_to(root)
                    except ValueError:
                        self.send_error_response(403, "access denied")
                        return
                    if not asset.is_file():
                        self.send_error_response(503, "web asset is not installed")
                        return
                    body = asset.read_bytes()
                    content_type = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
                    self.send_response(200)
                    if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
                        content_type += "; charset=utf-8"
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if router:
                    # Check for WebSocket upgrade
                    upgrade_header = self.headers.get("Upgrade", "").lower()
                    if upgrade_header == "websocket":
                        if server_instance and server_instance.ws_upgrade_handler:
                            # Mark that this request will be handled as WebSocket.
                            # Override finish() to avoid closing the underlying
                            # socket, which the WebSocket handler owns after this
                            # request returns.
                            self._ws_handoff = True
                            # WebSocket sessions are long-lived. Run each session outside
                            # the HTTP request worker so a connected client cannot occupy
                            # a request thread indefinitely.
                            ws_thread = threading.Thread(
                                target=server_instance.ws_upgrade_handler.handle_request,
                                args=(self.request,),
                                name="m20-websocket-client",
                                daemon=True,
                            )
                            ws_thread.start()
                            return
                        else:
                            self.send_error_response(503, "WebSocket not available")
                            return
                    
                    # Inject dependencies for handlers
                    self._gimbal = router.gimbal_adapter
                    self._video_manager = router.video_manager
                    self.server_instance = server_instance  # Reference to M20WebServer instance
                    router.route(self)  # type: ignore[arg-type]
                else:
                    self.send_error_response(503, "Service not ready")

            def send_error_response(self, status: int, message: str, code: str = "error") -> None:
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                body = {"status": "error", "error": message, "code": code}
                self.wfile.write(json.dumps(body).encode("utf-8"))

        return M20RequestHandler

    def stop(self) -> None:
        """Stop the web server."""
        if self.telemetry_adapter:
            self.telemetry_adapter.stop()
        if self.video_manager:
            try:
                self.video_manager.shutdown_sync()
            except Exception as exc:
                logger.warning("关闭视频管理器失败: %s", exc)
        if self.gimbal_adapter:
            self.gimbal_adapter.close()
        if self.server:
            self.server.shutdown()
            self.server = None
        logger.info("M20 Web Service stopped")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="M20 Patrol Robot Web Service")
    parser.add_argument(
        "--manifest",
        type=str,
        default="deploy/readonly-manifest.json",
        help="Path to manifest JSON file",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Override host from manifest",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Override port from manifest",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Load configuration
    config = ConfigLoader.load(args.manifest)

    # Override with command line args
    if args.host:
        config = replace(config, host=args.host)
    if args.port:
        config = replace(config, port=args.port)

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Start server
    server = M20WebServer(config)
    server.start()

if __name__ == '__main__':
    main()
