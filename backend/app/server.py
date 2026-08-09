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


logger = logging.getLogger(__name__)


class M20WebServer:
    """M20 patrol robot web service."""

    def __init__(self, config: WebServiceConfig) -> None:
        self.config = config
        self.telemetry_adapter: Optional[TelemetryAdapter] = None
        self.user_store: Optional[UserStore] = None
        self.auth_middleware: Optional[AuthMiddleware] = None
        self.router: Optional[ApiRouter] = None
        self.server: Optional[ThreadingHTTPServer] = None

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

        # Setup API router
        self.router = ApiRouter(
            user_store=self.user_store,
            auth_middleware=self.auth_middleware,
            telemetry_adapter=self.telemetry_adapter,
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
            "Auth enabled: %s",
            self.config.host, self.config.port,
            self.config.runtime_mode, self.config.read_only_mode,
            self.config.control_enabled, self.config.auth_enabled,
        )

        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
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
        config = WebServiceConfig(**{**vars(config), "host": args.host})
    if args.port:
        config = WebServiceConfig(**{**vars(config), "port": args.port})

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Start server
    server = M20WebServer(config)
    server.start()


if __name__ == "__main__":
    main()
