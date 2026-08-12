"""Real-time basic_server client for read-only status streaming.

Connects to AOS basic_server TCP 30001 and streams status messages
without sending any control commands. Navigation/motion commands remain
disabled until explicit field authorization.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
# Python 3.8 compatibility: UTC was added in Python 3.11
try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc
from typing import Any, Deque, Optional, Tuple

from backend.app.robot.basic_client import (
    BasicServerClient,
    BasicServerConfig,
    ClientStateError,
    DeploymentEvidence,
)
from backend.app.robot.status import parse_status_message, StatusResult
from backend.app.protocol.messages import PatrolMessage
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConnectionConfig:
    """Configuration for real AOS connection."""
    host: str
    tcp_port: int = 30001
    heartbeat_interval_s: float = 1.0
    stale_after_s: float = 3.0
    read_only: bool = True
    runtime_mode: str = "simulated"
    telemetry_receive_enabled: bool = True
    telemetry_tx_enabled: bool = False

    def __post_init__(self) -> None:
        if self.runtime_mode not in {"simulated", "realtime", "realtime_readonly"}:
            raise ValueError("runtime_mode must be simulated, realtime, or realtime_readonly")
        if type(self.read_only) is not bool:
            raise ValueError("read_only must be boolean")
        if type(self.telemetry_receive_enabled) is not bool:
            raise ValueError("telemetry_receive_enabled must be boolean")
        if type(self.telemetry_tx_enabled) is not bool:
            raise ValueError("telemetry_tx_enabled must be boolean")
        if self.telemetry_tx_enabled:
            raise ValueError("telemetry transmission is disabled in this release")
        # read_only is enforced per-request by handler gates, not at the
        # telemetry transport level. Transport-level read_only only governs
        # what the AOS subscription side sends back; control is gated by
        # BasicServerClient.control_enabled + explicit Web authorization.


@dataclass
class StatusSnapshot:
    """Latest parsed status data."""
    source: str  # "REAL" or "SIMULATED"
    connected: bool
    received_at: Optional[str]
    age_ms: Optional[int]
    basic: dict[str, Any] = field(default_factory=dict)
    motion: dict[str, Any] = field(default_factory=dict)
    device: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    nav_status: dict[str, Any] = field(default_factory=dict)
    position: dict[str, Any] = field(default_factory=dict)
    perception: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""


class TelemetryAdapter:
    """Real-time status adapter for basic_server TCP connection."""

    def __init__(self, config: ConnectionConfig, *, control_enabled: bool = False) -> None:
        self.config = config
        self.control_enabled = control_enabled
        self._client: Optional[BasicServerClient] = None
        self._snapshot = StatusSnapshot(
            source="NO_DATA",
            connected=False,
            received_at=None,
            age_ms=None,
        )
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._message_count = 0
        self._error_count = 0
        self._connection_count = 0
        self._reconnect_count = 0
        self._last_message_type: Optional[Tuple[int, int]] = None
        self._connection_received_messages = 0
        self._bytes_received = 0
        self._valid_frames = 0
        self._invalid_frames = 0
        self._tcp_connected = False
        self._nav_sync_callback = None
        self._motion_sync_callback = None
        self._client_callback = None

    def set_navigation_sync_callback(self, callback) -> None:
        """Set callback to sync navigation safety snapshot from telemetry."""
        self._nav_sync_callback = callback

    def set_motion_sync_callback(self, callback) -> None:
        """Set callback to sync motion control safety snapshot from telemetry."""
        self._motion_sync_callback = callback

    def set_client_callback(self, callback) -> None:
        """Provide the active TCP client to control services after connect."""
        self._client_callback = callback

    def _notify_client(self, client) -> None:
        if self._client_callback:
            self._client_callback(client)

    def _clear_client(self, client) -> None:
        if client is not None:
            try:
                client.close()
            except Exception as exc:
                logger.debug("关闭遥测客户端失败: %s", exc)
        if self._client is client:
            self._client = None
        self._tcp_connected = False
        self._notify_client(None)

    @property
    def snapshot(self) -> StatusSnapshot:
        with self._lock:
            return StatusSnapshot(**self._snapshot.__dict__)

    @property
    def message_count(self) -> int:
        return self._message_count

    @property
    def error_count(self) -> int:
        return self._error_count

    def start(self) -> None:
        """启动实时状态订阅。"""
        if self._running:
            return
        logger.info("启动遥测连接: %s:%s", self.config.host, self.config.tcp_port)
        logger.info("运行模式: %s", self.config.runtime_mode)
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止订阅并关闭连接。"""
        self._running = False
        if self._client:
            try:
                self._client.close()
            except Exception as exc:
                logger.warning("关闭遥测客户端时出错: %s", exc)
            finally:
                self._client = None
        if self._thread:
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                logger.warning("遥测线程未能正常终止，强制清理")
            self._thread = None

    def _run_loop(self) -> None:
        """主循环: 心跳 + 接收状态消息。"""
        if self.config.runtime_mode == "simulated":
            logger.info("模拟模式: 使用模拟数据")
            while self._running:
                self._update_snapshot_no_client(error="simulated mode: robot I/O disabled")
                time.sleep(0.5)
            return
        logger.info("连接 AOS: %s:%s", self.config.host, self.config.tcp_port)
        config = BasicServerConfig(
            host=self.config.host,
            tcp_port=self.config.tcp_port,
            control_enabled=self.control_enabled,
            stale_after_seconds=self.config.stale_after_s,
        )
        if not self.config.telemetry_receive_enabled:
            self._update_snapshot_no_client(error="telemetry receive disabled")
            return
        client = BasicServerClient(config)
        self._client = client
        self._notify_client(client)

        while self._running:
            try:
                client.connect(timeout_seconds=3.0, read_only=self.config.read_only)
                logger.info("遥测连接成功")
                self._tcp_connected = True
                self._connection_received_messages = 0
                self._connection_count += 1
                if self._connection_count > 1:
                    self._reconnect_count += 1
                self._update_snapshot(client, connected=True)
                
                while self._running:
                    # Receive active status messages
                    messages = client.receive_messages(timeout_seconds=0.5)
                    self._bytes_received = client.bytes_received
                    self._valid_frames = client.valid_frames
                    self._invalid_frames = client.invalid_frames
                    for msg in messages:
                        self._process_message(client, msg)
                    
                    # Send heartbeat every interval
                    if self.config.telemetry_tx_enabled:  # 已禁用，待协议样本确认后启用
                        time.sleep(self.config.heartbeat_interval_s / 2)
                        heartbeat = client.build_heartbeat()
                        try:
                            client.send_read_only(heartbeat)
                        except ClientStateError:
                            logger.warning("心跳发送失败，连接可能已断开")
                    
                    # Check staleness
                    now = datetime.now(UTC)
                    # A connection with no first frame yet is not stale; keep
                    # waiting so slow or quiet read-only endpoints do not
                    # churn through reconnects. Once a frame was received,
                    # the normal freshness threshold applies.
                    if client.last_received_at is not None and client.is_stale(now):
                        logger.warning("遥测数据超时，重新连接...")
                        self._update_snapshot(client, connected=True, stale=True)
                        client.close()
                        self._client = None
                        self._notify_client(None)
                        self._tcp_connected = False
                        client = BasicServerClient(config)
                        self._client = client
                        if self._client_callback:
                            self._client_callback(client)
                        break  # Reconnect on next iteration

            except ClientStateError as e:
                self._tcp_connected = False
                logger.warning("遥测连接错误: %s", e)
                self._clear_client(client)
                self._update_snapshot(client, connected=False, error=str(e))
                time.sleep(1)
            except Exception as e:
                self._tcp_connected = False
                logger.error("遥测异常: %s", e)
                self._clear_client(client)
                self._update_snapshot(client, connected=False, error=str(e))
                time.sleep(1)

        self._clear_client(client)

    def _update_snapshot_no_client(self, *, error: str) -> None:
        with self._lock:
            self._snapshot.connected = False
            self._snapshot.source = "SIMULATED" if self.config.runtime_mode == "simulated" else "NO_DATA"
            self._snapshot.received_at = None
            self._snapshot.error_message = error

    def _process_message(self, client: BasicServerClient, msg: PatrolMessage) -> None:
        """Parse and store status message."""
        try:
            result = parse_status_message(msg)
            with self._lock:
                self._message_count += 1
                self._connection_received_messages += 1
                self._last_message_type = (msg.message_type, msg.command)
                self._update_snapshot_inner(client, result)
                if self._message_count % 10 == 0:
                    logger.info("已接收 %d 条状态消息", self._message_count)

            # Callbacks may read the adapter again, so invoke them only after
            # releasing the snapshot lock.
            payload = self.get_status_payload()
            if self._nav_sync_callback:
                try:
                    self._nav_sync_callback(payload)
                except Exception as e:
                    logger.warning("导航安全快照同步失败: %s", e)
            if self._motion_sync_callback:
                try:
                    self._motion_sync_callback(payload)
                except Exception as e:
                    logger.warning("运动控制安全快照同步失败: %s", e)
        except Exception as e:
            with self._lock:
                self._error_count += 1
                self._snapshot.connected = False
                self._snapshot.source = "ERROR"
                self._snapshot.received_at = None
                self._snapshot.error_message = f"Parse error: {e}"

    def _update_snapshot(self, client: BasicServerClient, *, connected: bool, 
                         stale: bool = False, error: str = "") -> None:
        with self._lock:
            self._snapshot.connected = connected and not stale and self._connection_received_messages > 0
            self._snapshot.source = "REAL" if connected and not stale and self._connection_received_messages > 0 else (
                "STALE" if stale else "ERROR" if error else "NO_DATA"
            )
            self._snapshot.received_at = datetime.now(UTC).isoformat() if self._snapshot.connected else None
            self._snapshot.error_message = error
            if connected and client.last_received_at:
                age = (datetime.now(UTC) - client.last_received_at).total_seconds() * 1000
                self._snapshot.age_ms = int(age)

    def _update_snapshot_inner(self, client: BasicServerClient, result: StatusResult) -> None:
        """Update snapshot with parsed status data."""
        self._snapshot.source = "REAL"
        self._snapshot.connected = True
        self._snapshot.received_at = datetime.now(UTC).isoformat()
        
        data = result.data
        kind = result.kind
        if kind == "basic_status":
            self._snapshot.basic = data
        elif kind == "motion_status":
            self._snapshot.motion = data
        elif kind == "device_status":
            self._snapshot.device = data
        elif kind == "error_list":
            self._snapshot.errors = data.get("errors", [])
        elif kind == "navigation_status":
            self._snapshot.nav_status = data
        elif kind == "navigation_abnormal":
            self._snapshot.nav_status = data.get("nav_status", {})
            self._snapshot.position = data.get("location_status", {})
        elif kind == "position":
            self._snapshot.position = data
        elif kind == "perception":
            self._snapshot.perception = data
        
        # Calculate age
        if client.last_received_at:
            age = (datetime.now(UTC) - client.last_received_at).total_seconds() * 1000
            self._snapshot.age_ms = int(age)

    def get_status_payload(self) -> dict[str, Any]:
        """Get status payload for dashboard API."""
        with self._lock:
            snap = self._snapshot
            return {\
                "source": snap.source,\
                "connected": snap.connected,\
                "control_enabled": self.control_enabled,\
                "telemetry_tx_enabled": self.config.telemetry_tx_enabled,\
                "connection_state": "CONNECTED" if snap.connected else snap.source,
                "network_ready": self._connection_count > 0,
                "tcp_connected": self._tcp_connected,
                "bytes_received": self._bytes_received,
                "valid_frames": self._valid_frames,
                "invalid_frames": self._invalid_frames,
                "frame_valid": self._valid_frames > 0,
                "message_parsed": self._message_count > 0,
                "status_accepted": snap.source == "REAL" and snap.connected,
                "telemetry_fresh": snap.source == "REAL" and snap.connected and snap.age_ms is not None and 0 <= snap.age_ms < self.config.stale_after_s * 1000,
                "connection_count": self._connection_count,
                "reconnect_count": self._reconnect_count,
                "last_message_type": self._last_message_type,
                "received_at": snap.received_at,
                "age_ms": snap.age_ms,
                "message_count": self._message_count,
                "error_count": self._error_count,
                "data": {
                    "robot": "M20 Pro",
                    "navigation": "SUBSCRIBING" if snap.connected else "NOT_CONNECTED",
                    "basic": snap.basic,
                    "motion": snap.motion,
                    "device": snap.device,
                    "errors": snap.errors,
                    "nav_status": snap.nav_status,
                    "position": snap.position,
                    "perception": snap.perception,
                    "message": snap.error_message or (
                        "Connected to AOS basic_server. Status streaming active."
                        if snap.connected else
                        "Disconnected from AOS. Reconnecting..."
                    ),
                },
                "inspection_stats": {
                    "laps_today": snap.nav_status.get("loop_count", 0) if snap.nav_status else 0,
                    "coverage_rate": self._calculate_coverage(snap.position, snap.basic),
                    "anomaly_count": len(snap.errors) if snap.errors else 0,
                    "status": "active" if snap.connected else "idle",
                },
                "battery_percent": self._resolve_battery(snap.device),
            }

    @staticmethod
    def _calculate_coverage(position: dict[str, Any], basic: Optional[dict[str, Any]] = None) -> float:
        """Calculate coverage rate based on position and motion data."""
        if not position:
            return 0.0
        # Coverage is based on position validity and movement
        has_position = bool(position.get("pos_x") is not None or position.get("location"))
        # motion_state is in basic, not position
        motion_state = (basic or {}).get("motion_state", 0) if basic else 0
        is_moving = motion_state in (2, 3, 4)  # walking, jogging, stairs
        if has_position and is_moving:
            return 100.0
        elif has_position:
            return 50.0
        return 0.0

    @staticmethod
    def _resolve_battery(device: dict[str, Any]) -> int:
        """Extract battery percentage from device status data.

        Priority: BatteryList first level, then battery_status level.
        Fail-safe: return 0 when data is missing or invalid.
        """
        battery_list = device.get("battery_list")
        if isinstance(battery_list, list) and battery_list:
            levels = []
            for entry in battery_list:
                if isinstance(entry, dict):
                    level = entry.get("BatteryLevel")
                    if isinstance(level, (int, float)) and 0 <= level <= 100:
                        levels.append(level)
            if levels:
                return int(min(levels))
        status = device.get("battery_status")
        if isinstance(status, dict):
            level = status.get("BatteryLevel")
            if isinstance(level, (int, float)) and 0 <= level <= 100:
                return int(level)
        return 0
