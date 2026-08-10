"""Gimbal control module for M20 Pro - Soar Security WEB2.0 protocol."""

from __future__ import annotations

import base64
import ipaddress
import json
import logging
import socket
import threading
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GimbalConfig:
    """Configuration for Soar Security gimbal."""
    host: str = ""
    port: int = 80
    username: str = "admin"
    password: str = ""  # 必填，通过环境变量 M20_GIMBAL_PASSWORD 设置
    rtsp_url: str = ""
    thermal_rtsp_url: str = ""
    timeout: float = 5.0
    heartbeat_interval: float = 10.0
    discovered: bool = False


@dataclass
class DiscoveredGimbal:
    """Result of gimbal discovery."""
    host: str
    port: int = 80
    model: str = ""
    serial: str = ""
    firmware: str = ""
    rtsp_url: str = ""
    thermal_rtsp_url: str = ""
    accessible: bool = False


class SoarGimbalAdapter:
    """Adapter for Soar Security SR-UPA810T609 gimbal via WEB2.0 protocol."""

    @property
    def connected(self) -> bool:
        """Public accessor for connection state."""
        return self._connected

    # Common IP ranges to scan (priority order)
    # Only scan M20 robot network and common device networks
    SCAN_RANGES = [
        "10.21.31.0/24",  # M20 robot internal network (highest priority)
        "192.168.1.0/28",  # Limited scan: only first 16 IPs (devices, not PCs)
        "192.168.0.0/28",  # Limited scan
    ]

    # Skip these common non-device IPs
    SKIP_IPS = {
        ".1",    # Gateway/router
        ".254",  # Common gateway
        "255",   # Broadcast
    }

    # Soar Security default MAC OUI
    SOAR_OUI = ["00:1A:2B:3C", "00:0E:8B"]

    def __init__(self, config: Optional[GimbalConfig] = None) -> None:
        self.config = config or GimbalConfig()
        self._base_url = f"http://{self.config.host}:{self.config.port}" if self.config.host else ""
        self._path_prefix = "/merlin"
        self._auth = base64.b64encode(f"{self.config.username}:{self.config.password}".encode()).decode()
        self._session: Optional[str] = None
        self._lock = threading.RLock()
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._connected = False
        self._discovered: List[DiscoveredGimbal] = []

    def _request(self, method: str, path: str, data: Optional[dict] = None, params: Optional[dict] = None) -> tuple[int, dict]:
        """Send HTTP request and return (status_code, response_data)."""
        if not self._base_url:
            return 0, {}

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
            logger.debug("云台请求 %s %s -> HTTP %s", method, path, e.code)
            return e.code, {}
        except Exception as e:
            logger.debug("云台请求异常 %s %s: %s", method, path, e)
            return 0, {}

    # ---- Discovery ----

    def _ping_host(self, host: str, port: int = 80, timeout: float = 1.0) -> bool:
        """Check if host:port is reachable."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _get_gimbal_info(self, host: str) -> Optional[DiscoveredGimbal]:
        """Try to get gimbal info from a host."""
        url = f"http://{host}:{self.config.port}/merlin/GetFlyStateInfo.cgi"
        headers = {
            "Authorization": f"Basic {self._auth}",
            "Agent": "merlin HTTP agent",
        }
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                fly = data.get("FlyInfo", {})
                cam = data.get("CamerInfo", {})

                # Extract device info
                model = fly.get("model", "")
                serial = fly.get("sn", "")
                firmware = fly.get("firmware", "")

                return DiscoveredGimbal(
                    host=host,
                    port=self.config.port,
                    model=model,
                    serial=serial,
                    firmware=firmware,
                    rtsp_url=f"rtsp://{host}:554/id=1&type=0",
                    thermal_rtsp_url=f"rtsp://{host}:554/id=2&type=0",
                    accessible=True,
                )
        except Exception as e:
            logger.debug("获取云台信息失败 %s: %s", host, e)
            return None

    def discover(self, ranges: Optional[List[str]] = None, max_hosts: int = 100) -> List[DiscoveredGimbal]:
        """Scan network ranges to discover gimbal devices."""
        if ranges is None:
            ranges = self.SCAN_RANGES

        logger.info("开始扫描云台设备...")
        discovered: List[DiscoveredGimbal] = []
        seen: set = set()

        for network_str in ranges:
            try:
                network = ipaddress.ip_network(network_str, strict=False)
            except ValueError:
                continue

            logger.info("扫描网段: %s (最多%d个地址)", network_str, min(max_hosts, network.num_addresses))

            # Scan up to max_hosts per network
            scanned = 0
            for ip in network.hosts():
                if scanned >= max_hosts:
                    break

                host = str(ip)

                # Skip common non-device IPs
                skip = False
                for suffix in self.SKIP_IPS:
                    if host.endswith(suffix):
                        skip = True
                        break
                if skip:
                    continue

                if host in seen:
                    continue
                seen.add(host)

                # First check if host is alive
                if not self._ping_host(host, self.config.port):
                    continue

                # Try to get gimbal info
                info = self._get_gimbal_info(host)
                if info:
                    logger.info("发现云台设备: %s (型号: %s, 序列号: %s)", host, info.model, info.serial)
                    discovered.append(info)
                    scanned += 1

                    # Stop after finding first device (usually only one gimbal)
                    if len(discovered) >= 1:
                        break
                else:
                    scanned += 1

        self._discovered = discovered

        if discovered:
            logger.info("发现%d个云台设备", len(discovered))
        else:
            logger.warning("未发现云台设备，请确认网络配置或手动设置gimbal_host")

        return discovered

    def auto_connect(self) -> bool:
        """Auto-discover and connect to gimbal.

        Priority:
        1. Use configured host if set
        2. Try default Soar IP (192.168.1.108)
        3. Fall back to network scan
        """
        # Priority 1: Use configured host
        if self.config.host:
            logger.info("尝试直连云台: %s", self.config.host)
            if self.login():
                self.config.discovered = True
                return True
            logger.warning("直连失败: %s，尝试默认IP...", self.config.host)

        # Priority 2: Try default Soar IP
        default_ip = "192.168.1.108"
        logger.info("尝试默认IP: %s", default_ip)
        self.config.host = default_ip
        self._base_url = f"http://{default_ip}:{self.config.port}"
        if self.login():
            self.config.discovered = True
            logger.info("云台已连接: %s", default_ip)
            return True
        logger.warning("默认IP连接失败，尝试网络扫描...")

        # Priority 3: Network scan fallback
        return self._fallback_scan()

    def _fallback_scan(self) -> bool:
        """Fallback to network scan if default IP fails."""
        found = self.discover()
        if not found:
            return False

        # Use first discovered device
        self.config.host = found[0].host
        self._base_url = f"http://{self.config.host}:{self.config.port}"
        self.config.rtsp_url = found[0].rtsp_url
        self.config.thermal_rtsp_url = found[0].thermal_rtsp_url
        self.config.discovered = True

        logger.info("云台自动发现: %s (型号: %s)", self.config.host, found[0].model)

        # Connect
        return self.login()

    # ---- Connection ----

    def login(self) -> bool:
        """Login to gimbal and get session."""
        if not self._base_url:
            logger.warning("云台地址未配置")
            return False

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
                    logger.info("云台登录成功: %s", self.config.host)
                    self._start_heartbeat()
                else:
                    logger.warning("云台登录响应缺少 Session 字段: %s", data)
                return self._session is not None
        except urllib.error.HTTPError as e:
            logger.warning("云台登录 HTTP 错误: %s", e.code)
            return False
        except Exception as e:
            logger.warning("云台登录失败: %s", e)
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
                    logger.warning("心跳失败，重新登录")
                    self.login()
        except Exception as e:
            logger.error("心跳错误: %s", e)
            self.login()

    def _start_heartbeat(self) -> None:
        """Start heartbeat thread."""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        self._stop_event.clear()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        logger.info("心跳已启动 (间隔: %.1fs)", self.config.heartbeat_interval)

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
        logger.info("云台连接已关闭")

    def __enter__(self):
        self.auto_connect()
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
            logger.error("无效方向: %s", direction)
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
                "connected": self._connected,
                "yaw": fly.get("yaw", 0),
                "pitch": fly.get("pitch", 0),
                "roll": fly.get("roll", 0),
                "zoom": cam.get("zoom", 1),
            }
        return {"connected": False}

    def get_device_info(self) -> dict:
        """Get device info (CPU, memory, storage)."""
        status, data = self._request("GET", "GetDeviceState.cgi")
        if status == 200:
            sys_state = data.get("DeviceState", {}).get("SystemState", {})
            return {
                "connected": self._connected,
                "model": self.config.host,
                "cpu": sys_state.get("CPU", 0),
                "mem": sys_state.get("MEM", 0),
                "storage_total": sys_state.get("totalvolume", "0GB"),
                "storage_free": sys_state.get("undistributed", "0GB"),
            }
        return {"connected": False}

    def get_video_urls(self) -> dict:
        """Get RTSP video stream URLs."""
        return {
            "visible_light": self.config.rtsp_url or f"rtsp://{self.config.host}:554/id=1&type=0",
            "thermal": self.config.thermal_rtsp_url or f"rtsp://{self.config.host}:554/id=2&type=0",
        }

    def enable_motor(self, enable: int) -> bool:
        """Enable/disable motor: 0=off, 1=start, 2=restart."""
        data = {"Motor": {"Enable": enable}}
        status, _ = self._request("POST", "SetPtzAbility.cgi", data=data)
        return status == 200

    def scan(self, ranges: Optional[List[str]] = None) -> List[dict]:
        """Scan and return list of discovered gimbals as dicts."""
        discovered = self.discover(ranges)
        return [
            {
                "host": g.host,
                "port": g.port,
                "model": g.model,
                "serial": g.serial,
                "firmware": g.firmware,
                "rtsp_url": g.rtsp_url,
                "accessible": g.accessible,
            }
            for g in discovered
        ]
