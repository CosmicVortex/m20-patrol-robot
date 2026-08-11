"""API route for M20 Pro patrol robot.

Routes HTTP requests to appropriate handler classes.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from backend.app.auth.middleware import AuthMiddleware
from backend.app.auth.store import UserStore
from backend.app.config import WebServiceConfig
from backend.app.robot.telemetry import TelemetryAdapter
from backend.app.navigation.service import NavigationService
from backend.app.api.handlers import (
    AuthLoginHandler,
    AuthLogoutHandler,
    AuthMeHandler,
    BaseHandler,
    DevicesListHandler,
    EmergencyStopHandler,
    HealthHandler,
    NavigationAuthorizeHandler,
    NavigationCancelHandler,
    NavigationStatusHandler,
    NavigationTaskHandler,
    StatusLatestHandler,
    VideoStatusHandler,
)
from backend.app.api.extended_handlers import (
    GimbalAngleHandler,
    GimbalConnectHandler,
    GimbalDeviceInfoHandler,
    GimbalMoveHandler,
    GimbalScanHandler,
    GimbalStateHandler,
    GimbalVideoHandler,
    GimbalZoomHandler,
    InspectionPointsHandler,
    SystemInfoHandler,
    TimelineHandler,
    UserChangePasswordHandler,
    UserListHandler,
    WorkOrdersCreateHandler,
    WorkOrdersListHandler,
    WorkOrdersUpdateHandler,
)
from backend.app.gimbal.adapter import SoarGimbalAdapter
from backend.app.video.stream_manager import VideoStreamManager
from backend.app.motion.handlers import (
    MotionStateHandler,
    GaitSwitchHandler,
    AxisControlHandler,
    LightControlHandler,
    ModeSwitchHandler,
    ChargeControlHandler,
    SleepModeHandler,
    MotionStatusHandler,
    MotionAuthorizeHandler,
    MotionDeauthorizeHandler,
)

logger = logging.getLogger(__name__)


class ApiRouter:
    """Routes HTTP requests to handler classes based on path."""

    HANDLERS: dict[str, type[BaseHandler]] = {
        "/api/v1/health": HealthHandler,
        "/api/v1/auth/login": AuthLoginHandler,
        "/api/v1/auth/logout": AuthLogoutHandler,
        "/api/v1/auth/me": AuthMeHandler,
        "/api/v1/status/latest": StatusLatestHandler,
        "/api/v1/devices": DevicesListHandler,
        "/api/v1/navigation/status": NavigationStatusHandler,
        "/api/v1/navigation/authorize": NavigationAuthorizeHandler,
        "/api/v1/navigation/tasks": NavigationTaskHandler,
        "/api/v1/navigation/cancel": NavigationCancelHandler,
        "/api/v1/emergency/stop": EmergencyStopHandler,
        "/api/v1/video": VideoStatusHandler,
        # Extended handlers
        "/api/v1/work-orders": WorkOrdersListHandler,
        "/api/v1/work-orders/create": WorkOrdersCreateHandler,
        "/api/v1/work-orders/update": WorkOrdersUpdateHandler,
        "/api/v1/inspection-points": InspectionPointsHandler,
        "/api/v1/timeline": TimelineHandler,
        "/api/v1/users": UserListHandler,
        "/api/v1/users/password": UserChangePasswordHandler,
        "/api/v1/system/info": SystemInfoHandler,
        # Gimbal handlers (extended versions take precedence)
        "/api/v1/gimbal/state": GimbalStateHandler,
        "/api/v1/gimbal/move": GimbalMoveHandler,
        "/api/v1/gimbal/zoom": GimbalZoomHandler,
        "/api/v1/gimbal/angle": GimbalAngleHandler,
        "/api/v1/gimbal/device/info": GimbalDeviceInfoHandler,
        "/api/v1/gimbal/video": GimbalVideoHandler,
        "/api/v1/gimbal/scan": GimbalScanHandler,
        "/api/v1/gimbal/connect": GimbalConnectHandler,
        # Motion control handlers
        "/api/v1/motion/state": MotionStateHandler,
        "/api/v1/motion/gait": GaitSwitchHandler,
        "/api/v1/motion/axis": AxisControlHandler,
        "/api/v1/motion/light": LightControlHandler,
        "/api/v1/motion/mode": ModeSwitchHandler,
        "/api/v1/motion/charge": ChargeControlHandler,
        "/api/v1/motion/sleep": SleepModeHandler,
        "/api/v1/motion/status": MotionStatusHandler,
        "/api/v1/motion/authorize": MotionAuthorizeHandler,
        "/api/v1/motion/deauthorize": MotionDeauthorizeHandler,
    }

    # WebSocket paths
    WS_HANDLERS: dict[str, Any] = {}

    def __init__(
        self,
        user_store: UserStore,
        auth_middleware: AuthMiddleware,
        telemetry_adapter: Optional[TelemetryAdapter] = None,
        nav_service: Optional[NavigationService] = None,
        config: Optional[WebServiceConfig] = None,
        gimbal_adapter: Optional[SoarGimbalAdapter] = None,
        video_manager: Optional[VideoStreamManager] = None,
        server_instance: Any = None,
        motion_service: Any = None,
    ) -> None:
        self.user_store = user_store
        self.auth_middleware = auth_middleware
        self.telemetry_adapter = telemetry_adapter
        self.nav_service = nav_service
        self.config = config
        self.gimbal_adapter = gimbal_adapter
        self.video_manager = video_manager
        self.server_instance = server_instance
        self.motion_service = motion_service

    def route(self, handler: BaseHandler) -> None:
        """Route the request to the appropriate handler."""
        handler_class = self.HANDLERS.get(handler.path)
        if handler_class is None:
            # Try prefix matching
            for prefix, cls in self.HANDLERS.items():
                if handler.path.startswith(prefix):
                    handler_class = cls
                    break

        if handler_class is None:
            handler.send_error_response(404, "Not found")
            return

        # Inject dependencies
        handler.auth_middleware = self.auth_middleware
        handler.user_store = self.user_store
        handler.telemetry_adapter = self.telemetry_adapter
        handler.nav_service = self.nav_service
        handler.config = self.config
        handler.gimbal_adapter = self.gimbal_adapter
        handler.video_manager = self.video_manager
        handler.server_instance = self.server_instance
        handler.motion_service = self.motion_service

        # Dispatch on the live request handler.
        method = handler.command.lower()
        handler_method = f"do_{method.upper()}"
        if hasattr(handler_class, handler_method):
            getattr(handler_class, handler_method)(handler)
        else:
            handler.send_error_response(405, "Method not allowed")
