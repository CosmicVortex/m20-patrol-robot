"""Gimbal control module for M20 Pro - Soar Security WEB2.0 protocol."""

from __future__ import annotations

import base64
import json
import logging
import threading
import urllib.request
import urllib.error
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

os.environ['no_proxy'] = '*'


@dataclass
class GimbalConfig:
    """Configuration for Soar Security gimbal."""
    host: str = "192.168.1.108"
    port: int = 80
    username: str = "admin"
    password: str = "123456"
    rtsp_url: str = "rtsp://192.168.1.108:554/id=1&type=0"
    thermal_rtsp_url: str = "rtsp://192.168.1.108:554/id=2&type=0"
    timeout: float = 5.0
    heartbeat_interval: float = 10.0


class SoarGimbalAdapter:
    """Adapter for Soar Security SR-UPA810T609 gimbal via WEB2.0 protocol."""

    def __init__(self, config: GimbalConfig) -> None:
        self.config = config
        self._base_url = f"http://{config.host}:{config.port}"
        self._path_prefix = "/merlin"
        self._auth = base64.b64encode(f"{config.username}:{config.password}".encode()).decode()
        self._session: Optional[str] = None
        self._lock = threading.RLock()
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._connected = False

    def _request(self, method: str, path: str, data: Optional[dict] = None, params: Optional[dict] = None) -> tuple[int, dict]:
        """Send HTTP request and return (status_code, response_data)."""
        url = f"{self._base_url}{self._path_prefix}/{path}"
        headers = {
            "Authorization": f"Basic {self._auth}",
            "Agent": "merlin HTTP agent",
            "Content-Type": "application/json",
        }
        if self._session:
            headers["Session"] = self._session

        req_data = None
        if data is not None:
            req_data = json.dumps(data).encode('utf-8')

        url_with_params = url
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            url_with_params = f"{url}?{query}"

        try:
            req = urllib.request.Request(url_with_params, data=req_data, headers=headers, method=method.upper())
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                body = resp.read().decode('utf-8')
                try:
                    return resp.status, json.loads(body)
                except json.JSONDecodeError:
                    return resp.status, {}
        except urllib.error.HTTPError as e:
            logger.error("Gimbal request failed: %s %s -> %s", method, path, e.code)
            return e.code, {}
        except Exception as e:
            logger.error("Gimbal request error: %s %s - %s", method, path, e)
            return 0, {}

    def login(self) -> bool:
        """Login to gimbal and get session."""
        url = f"{self._base_url}{self._path_prefix}/Login.cgi?Type=WEB&Expires=30"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                session = data.get("Session") or (data.get("result") or {}).get("Session")
                with self._lock:
                    self._session = str(session) if session else None
                    self._connected = self._session is not None
                if self._session:
                    logger.info("Gimbal session obtained")
                    self._start_heartbeat()
                return self._session is not None
        except Exception as e:
            logger.warning("Gimbal login failed: %s", e)
            return False

    def _heartbeat_loop(self) -> None:
        """Heartbeat loop."""
        while not self._stop_event.wait(timeout=self.config.heartbeat_interval):
            with self._lock:
                session = self._session
            if not session:
                continue
            self.heartbeat()

    def heartbeat(self) -> None:
        """Send heartbeat."""
        url = f"{self._base_url}{self._path_prefix}/Heartbeat.cgi"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                if resp.status != 200:
                    logger.warning("Heartbeat failed, re-login")
                    self.login()
        except Exception as e:
            logger.error("Heartbeat error: %s", e)
            self.login()

    def _start_heartbeat(self) -> None:
        """Start heartbeat thread."""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        self._stop_event.clear()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        logger.info("Heartbeat started (interval: %.1fs)", self.config.heartbeat_interval)

    def stop_heartbeat(self) -> None:
        """Stop heartbeat."""
        self._stop_event.set()
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=3)
            self._heartbeat_thread = None

    def close(self) -> None:
        """Close gimbal connection."""
        self.stop_heartbeat()
        with self._lock:
            self._session = None
            self._connected = False
        logger.info("Gimbal connection closed")

    def __enter__(self):
        self.login()
        return self

    def __exit__(self, *args):
        self.close()

    # ---- PTZ Control ----

    def set_angle(self, yaw: float, pitch: float, roll: float = 0) -> bool:
        """Set gimbal angle (absolute)."""
        data = {"Angle": {"yaw": yaw, "pitch": pitch, "roll": roll}}
        status, _ = self._request("POST", "SetPtzangle.cgi", data=data)
        return status == 200

    def move_direction(self, direction: str, speed: int = 5) -> bool:
        """Move gimbal direction: up/down/left/right/stop."""
        if direction not in ("up", "down", "left", "right", "stop"):
            logger.error("Invalid direction: %s", direction)
            return False
        data = {"Direction": {"ptz_opt": direction, "speed": speed}}
        status, _ = self._request("POST", "SetPtzDirection.cgi", data=data)
        return status == 200

    def zoom(self, operation: int, speed: int = 5) -> bool:
        """Zoom control: 9=zoom_in, 10=zoom_out."""
        params = {"operation": operation, "speed": speed, "channelno": 0, "value": 0}
        status, _ = self._request("GET", "PtzCtrl.cgi", params=params)
        return status == 200

    def zoom_to(self, zoom_level: int) -> bool:
        """Set zoom level directly (1-10)."""
        zoom_level = max(1, min(zoom_level, 10))
        params = {"zoom": zoom_level, "channelno": 0}
        status, _ = self._request("GET", "ZoomCtrl.cgi", params=params)
        return status == 200

    def get_state(self) -> dict:
        """Get current gimbal state."""
        status, data = self._request("GET", "GetFlyStateInfo.cgi")
        if status == 200:
            fly = data.get("FlyInfo", {})
            cam = data.get("CamerInfo", {})
            return {
                "yaw": fly.get("yaw", 0),
                "pitch": fly.get("pitch", 0),
                "roll": fly.get("roll", 0),
                "zoom": cam.get("zoom", 1),
            }
        return {}

    def get_device_info(self) -> dict:
        """Get device info (CPU, memory, storage)."""
        status, data = self._request("GET", "GetDeviceState.cgi")
        if status == 200:
            sys_state = data.get("DeviceState", {}).get("SystemState", {})
            return {
                "cpu": sys_state.get("CPU", 0),
                "mem": sys_state.get("MEM", 0),
                "storage_total": sys_state.get("totalvolume", "0GB"),
                "storage_free": sys_state.get("undistributed", "0GB"),
            }
        return {}

    def enable_motor(self, enable: int) -> bool:
        """Enable/disable motor: 0=off, 1=start, 2=restart."""
        data = {"Motor": {"Enable": enable}}
        status, _ = self._request("POST", "SetPtzAbility.cgi", data=data)
        return status == 200
