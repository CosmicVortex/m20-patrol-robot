"""Motion control API handlers for M20 Pro robot.

Provides HTTP endpoints for motion control commands:
- POST /api/v1/motion/state - Switch motion state (stand/lie_down/soft_estop)
- POST /api/v1/motion/gait - Switch gait
- POST /api/v1/motion/axis - Send axis control command
- POST /api/v1/motion/light - Control lights
- POST /api/v1/motion/mode - Switch usage mode
- POST /api/v1/motion/charge - Control auto charge
- POST /api/v1/motion/sleep - Set sleep mode
- GET /api/v1/motion/status - Get motion control status
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from backend.app.api.base_handler import BaseHandler
from backend.app.motion.service import MotionControlService

logger = logging.getLogger(__name__)


class MotionStateHandler(BaseHandler):
    """Handle motion state switching requests."""

    def do_POST(self) -> None:
        if not self.config or not self.config.control_enabled or self.config.read_only_mode:
            self.send_error_response(403, "控制未启用")
            return

        auth = self._authenticate()
        if auth is None:
            return
        # 测试阶段：允许所有用户执行控制操作
        # if auth.role != "admin":
        #     self.send_error_response(403, "需要管理员权限")
        #     return

        try:
            data = self._parse_json_body()
        except Exception as e:
            self.send_error_response(400, f"请求解析失败: {e}")
            return

        state = data.get("state")
        if state is None:
            self.send_error_response(400, "缺少 state 参数")
            return

        service: Optional[MotionControlService] = getattr(self.server_instance, "motion_service", None)
        if service is None:
            self.send_error_response(503, "运动控制服务未初始化")
            return

        result = service.motion_state_switch(int(state))
        self.send_raw_json_response(200, result)


class GaitSwitchHandler(BaseHandler):
    """Handle gait switching requests."""

    def do_POST(self) -> None:
        if not self.config or not self.config.control_enabled or self.config.read_only_mode:
            self.send_error_response(403, "控制未启用")
            return

        auth = self._authenticate()
        if auth is None:
            return
        # 测试阶段：允许所有用户执行控制操作
        # if auth.role != "admin":
        #     self.send_error_response(403, "需要管理员权限")
        #     return

        try:
            data = self._parse_json_body()
        except Exception as e:
            self.send_error_response(400, f"请求解析失败: {e}")
            return

        gait = data.get("gait")
        if gait is None:
            self.send_error_response(400, "缺少 gait 参数")
            return

        service: Optional[MotionControlService] = getattr(self.server_instance, "motion_service", None)
        if service is None:
            self.send_error_response(503, "运动控制服务未初始化")
            return

        result = service.gait_switch(int(gait))
        self.send_raw_json_response(200, result)


class AxisControlHandler(BaseHandler):
    """Handle axis control requests."""

    def do_POST(self) -> None:
        if not self.config or not self.config.control_enabled or self.config.read_only_mode:
            self.send_error_response(403, "控制未启用")
            return

        auth = self._authenticate()
        if auth is None:
            return
        # 测试阶段：允许所有用户执行控制操作
        # if auth.role != "admin":
        #     self.send_error_response(403, "需要管理员权限")
        #     return

        try:
            data = self._parse_json_body()
        except Exception as e:
            self.send_error_response(400, f"请求解析失败: {e}")
            return

        x = data.get("x", 0.0)
        y = data.get("y", 0.0)
        yaw = data.get("yaw", 0.0)

        service: Optional[MotionControlService] = getattr(self.server_instance, "motion_service", None)
        if service is None:
            self.send_error_response(503, "运动控制服务未初始化")
            return

        result = service.axis_control(float(x), float(y), float(yaw))
        self.send_raw_json_response(200, result)


class LightControlHandler(BaseHandler):
    """Handle light control requests."""

    def do_POST(self) -> None:
        if not self.config or not self.config.control_enabled or self.config.read_only_mode:
            self.send_error_response(403, "控制未启用")
            return

        auth = self._authenticate()
        if auth is None:
            return
        # 测试阶段：允许所有用户执行控制操作
        # if auth.role != "admin":
        #     self.send_error_response(403, "需要管理员权限")
        #     return

        try:
            data = self._parse_json_body()
        except Exception as e:
            self.send_error_response(400, f"请求解析失败: {e}")
            return

        front = data.get("front", 0)
        back = data.get("back", 0)

        service: Optional[MotionControlService] = getattr(self.server_instance, "motion_service", None)
        if service is None:
            self.send_error_response(503, "运动控制服务未初始化")
            return

        result = service.light_control(int(front), int(back))
        self.send_raw_json_response(200, result)


class ModeSwitchHandler(BaseHandler):
    """Handle mode switching requests."""

    def do_POST(self) -> None:
        if not self.config or not self.config.control_enabled or self.config.read_only_mode:
            self.send_error_response(403, "控制未启用")
            return

        auth = self._authenticate()
        if auth is None:
            return
        # 测试阶段：允许所有用户执行控制操作
        # if auth.role != "admin":
        #     self.send_error_response(403, "需要管理员权限")
        #     return

        try:
            data = self._parse_json_body()
        except Exception as e:
            self.send_error_response(400, f"请求解析失败: {e}")
            return

        mode = data.get("mode")
        if mode is None:
            self.send_error_response(400, "缺少 mode 参数")
            return

        service: Optional[MotionControlService] = getattr(self.server_instance, "motion_service", None)
        if service is None:
            self.send_error_response(503, "运动控制服务未初始化")
            return

        result = service.mode_switch(int(mode))
        self.send_raw_json_response(200, result)


class ChargeControlHandler(BaseHandler):
    """Handle auto charge control requests."""

    def do_POST(self) -> None:
        if not self.config or not self.config.control_enabled or self.config.read_only_mode:
            self.send_error_response(403, "控制未启用")
            return

        auth = self._authenticate()
        if auth is None:
            return
        # 测试阶段：允许所有用户执行控制操作
        # if auth.role != "admin":
        #     self.send_error_response(403, "需要管理员权限")
        #     return

        try:
            data = self._parse_json_body()
        except Exception as e:
            self.send_error_response(400, f"请求解析失败: {e}")
            return

        charge = data.get("charge")
        if charge is None:
            self.send_error_response(400, "缺少 charge 参数")
            return

        service: Optional[MotionControlService] = getattr(self.server_instance, "motion_service", None)
        if service is None:
            self.send_error_response(503, "运动控制服务未初始化")
            return

        result = service.charge_control(int(charge))
        self.send_raw_json_response(200, result)


class SleepModeHandler(BaseHandler):
    """Handle sleep mode setting requests."""

    def do_POST(self) -> None:
        if not self.config or not self.config.control_enabled or self.config.read_only_mode:
            self.send_error_response(403, "控制未启用")
            return

        auth = self._authenticate()
        if auth is None:
            return
        # 测试阶段：允许所有用户执行控制操作
        # if auth.role != "admin":
        #     self.send_error_response(403, "需要管理员权限")
        #     return

        try:
            data = self._parse_json_body()
        except Exception as e:
            self.send_error_response(400, f"请求解析失败: {e}")
            return

        sleep = data.get("sleep", False)
        auto = data.get("auto", False)
        time = data.get("time", 10)

        service: Optional[MotionControlService] = getattr(self.server_instance, "motion_service", None)
        if service is None:
            self.send_error_response(503, "运动控制服务未初始化")
            return

        result = service.sleep_mode(bool(sleep), bool(auto), int(time))
        self.send_raw_json_response(200, result)


class MotionStatusHandler(BaseHandler):
    """Handle motion control status requests."""

    def do_GET(self) -> None:
        service: Optional[MotionControlService] = getattr(self.server_instance, "motion_service", None)
        if service is None:
            self.send_error_response(503, "运动控制服务未初始化")
            return

        result = service.get_status()
        self.send_raw_json_response(200, result)


class MotionAuthorizeHandler(BaseHandler):
    """Handle motion control authorization requests."""

    def do_POST(self) -> None:
        if not self.config or not self.config.control_enabled or self.config.read_only_mode:
            self.send_error_response(403, "控制未启用")
            return

        auth = self._authenticate()
        if auth is None:
            self.send_error_response(401, "未授权访问")
            return

        # 测试阶段：允许匿名用户执行授权操作
        # 如果需要限制权限，取消下面的注释
        # if auth.role == "anonymous":
        #     self.send_error_response(403, "匿名模式不允许执行控制操作，请先登录")
        #     return

        # if auth.role != "admin":
        #     self.send_error_response(403, "需要管理员权限")
        #     return

        service: Optional[MotionControlService] = getattr(self.server_instance, "motion_service", None)
        if service is None:
            self.send_error_response(503, "运动控制服务未初始化")
            return

        # Get operator from auth
        if auth.user:
            operator = auth.user.username
        else:
            self.send_error_response(401, "无法获取用户信息")
            return

        result = service.authorize(operator)
        self.send_raw_json_response(200, result)


class MotionDeauthorizeHandler(BaseHandler):
    """Handle motion control deauthorization requests."""

    def do_POST(self) -> None:
        if not self.config or not self.config.control_enabled or self.config.read_only_mode:
            self.send_error_response(403, "控制未启用")
            return

        auth = self._authenticate()
        if auth is None:
            return

        # 测试阶段：允许所有用户执行控制操作
        # if auth.role != "admin":
        #     self.send_error_response(403, "需要管理员权限")
        #     return

        service: Optional[MotionControlService] = getattr(self.server_instance, "motion_service", None)
        if service is None:
            self.send_error_response(503, "运动控制服务未初始化")
            return

        result = service.deauthorize()
        self.send_raw_json_response(200, result)
