"""M20 Web service - main entry point.

Starts the HTTP server with authentication, telemetry, and API routes.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
import os
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.auth.middleware import AuthMiddleware
from backend.app.auth.store import UserStore
from backend.app.config import ConfigLoader, WebServiceConfig
from backend.app.robot.telemetry import TelemetryAdapter, ConnectionConfig
from backend.app.api.router import ApiRouter
from backend.app.api.handlers import BaseHandler
from backend.app.navigation.service import NavigationService
from backend.app.navigation.v010 import NavigationSafetySnapshot
from backend.app.robot.basic_client import BasicServerConfig
from backend.app.gimbal.adapter import SoarGimbalAdapter, GimbalConfig
from backend.app.video.stream_manager import VideoStreamManager

logger = logging.getLogger(__name__)


class M20WebServer:
    """M20 patrol robot web service."""

    def __init__(self, config: WebServiceConfig) -> None:
        self.config = config
        self.telemetry_adapter: Optional[TelemetryAdapter] = None
        self.user_store: Optional[UserStore] = None
        self.auth_middleware: Optional[AuthMiddleware] = None
        self.nav_service: Optional[NavigationService] = None
        self.router: Optional[ApiRouter] = None
        self.server: Optional[ThreadingHTTPServer] = None
        self.video_manager = None

    def setup(self) -> None:
        """Initialize all components."""
        # Setup authentication store
        db_path = Path(self.config.auth_db_path or (Path(__file__).parent / "data" / "m20_auth.db"))
        self.user_store = UserStore(db_path, session_ttl_s=self.config.session_ttl_s)

        # Never ship a known default password. Provision an admin explicitly
        # through M20_ADMIN_PASSWORD on the target host, then remove the env.
        self._ensure_admin_user()

        # Setup auth middleware
        self.auth_middleware = AuthMiddleware(
            self.user_store,
            allow_anonymous=self.config.allow_anonymous,
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
        self.telemetry_adapter = TelemetryAdapter(telemetry_config)

        # Setup navigation service (disabled by default until authorized)
        basic_config = BasicServerConfig(
            host=self.config.aos_host,
            tcp_port=self.config.aos_port,
            control_enabled=self.config.control_enabled,
            stale_after_seconds=self.config.stale_after_s,
        )
        safety_snapshot = NavigationSafetySnapshot(
            control_enabled=self.config.control_enabled,
            field_authorization="pending_field_authorization",
            tcp_connected=False,
            location_normal=False,
            obstacle_avoidance_active=True,
            hard_estop_active=False,
            protective_fault_active=False,
            battery_percent=100,
            active_task=False,
        )
        from backend.app.robot.basic_client import BasicServerClient
        basic_client = BasicServerClient(basic_config)
        self.nav_service = NavigationService(basic_client, safety_snapshot)

        # Setup video stream manager
        self.video_manager = VideoStreamManager(allow_real_io=self.config.allow_real_io)

        # Setup gimbal adapter with auto-discovery support (MUST be before router)
        self.gimbal_adapter: Optional[SoarGimbalAdapter] = None
        if self.config.gimbal_host:
            logger.info("配置云台地址: %s", self.config.gimbal_host)
            gimbal_config = GimbalConfig(
                host=self.config.gimbal_host,
                username=self.config.gimbal_username,
                password=self.config.gimbal_password,
            )
            self.gimbal_adapter = SoarGimbalAdapter(gimbal_config)
            if self.gimbal_adapter.auto_connect():
                logger.info("云台已连接: %s", self.config.gimbal_host)
            else:
                logger.warning("云台连接失败，可使用 /api/v1/gimbal/scan 扫描")
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
        )

    def _ensure_admin_user(self) -> None:
        """Create default admin user if not exists."""
        if self.user_store is None:
            return
        password = os.environ.get("M20_ADMIN_PASSWORD")
        if not password:
            logger.warning("No M20_ADMIN_PASSWORD supplied; no default administrator will be created")
            return
        try:
            self.user_store.authenticate("admin", password)
        except Exception:
            try:
                admin = self.user_store.create_user("admin", password, "admin")
                logger.info("Provisioned administrator account: %s", admin.username)
            except Exception as exc:
                logger.warning("Failed to provision administrator: %s", exc)

    def start(self) -> None:
        """Start the web server."""
        self.setup()

        if self.telemetry_adapter:
            self.telemetry_adapter.start()

        # Setup request handler
        handler = self._create_handler()

        # Start HTTP server
        self.server = ThreadingHTTPServer(
            (self.config.host, self.config.port),
            handler,
        )

        logger.info(
            "M20 Web Service starting on %s:%s\n"
            "Runtime mode: %s\n"
            "Read-only: %s\n"
            "Control enabled: %s\n"
            "Auth enabled: %s\n"
            "Gimbal: %s",
            self.config.host, self.config.port,
            self.config.runtime_mode, self.config.read_only_mode,
            self.config.control_enabled, self.config.auth_enabled,
            self.config.gimbal_host or "未配置",
        )

        logger.info("Web服务已启动: %s:%s", self.config.host, self.config.port)
        logger.info("遥测目标: %s:%s (模式: %s)", self.config.aos_host, self.config.aos_port, self.config.runtime_mode)
        logger.info("安全配置: 只读模式=%s, 控制命令=%s", self.config.read_only_mode, self.config.control_enabled)

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            logger.info("收到停止信号，正在关闭服务...")
            self.stop()

    def _create_handler(self) -> type[BaseHTTPRequestHandler]:
        """Create request handler class with injected dependencies."""
        config = self.config
        router = self.router

        class M20RequestHandler(BaseHandler):
            def log_message(self, format: str, *args: object) -> None:
                logger.info("%s %s - %s", self.command, self.path, format % args)

            def do_GET(self) -> None:
                self._handle_request()

            def do_POST(self) -> None:
                self._handle_request()

            def do_PUT(self) -> None:
                self._handle_request()

            def do_DELETE(self) -> None:
                self._handle_request()

            def _handle_request(self) -> None:
                if self.path in ("/", "/index.html"):
                    root = Path(config.static_root)
                    index = root / "index.html"
                    if not index.is_file():
                        self.send_error_response(503, "web asset is not installed")
                        return
                    body = index.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if router:
                    # Inject dependencies for handlers
                    if hasattr(router, 'gimbal_adapter'):
                        self._gimbal = router.gimbal_adapter
                    if hasattr(router, 'video_manager'):
                        self._video_manager = router.video_manager
                    router.route(self)  # type: ignore[arg-type]
                else:
                    self.send_error_response(503, "Service not ready")

            def send_error_response(self, status: int, message: str, code: str = "error") -> None:
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                import json as json_mod
                body = {"status": "error", "error": message, "code": code}
                self.wfile.write(json_mod.dumps(body).encode("utf-8"))

        return M20RequestHandler

    def stop(self) -> None:
        """Stop the web server."""
        if self.telemetry_adapter:
            self.telemetry_adapter.stop()
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
