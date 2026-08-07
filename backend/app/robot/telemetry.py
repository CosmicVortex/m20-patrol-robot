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
from typing import Any, Deque

from backend.app.robot.basic_client import (
    BasicServerClient,
    BasicServerConfig,
    ClientStateError,
    DeploymentEvidence,
)
from backend.app.robot.status import parse_status_message, StatusResult
from backend.app.protocol.messages import PatrolMessage


@dataclass(frozen=True)
class ConnectionConfig:
    """Configuration for real AOS connection."""
    host: str
    tcp_port: int = 30001
    heartbeat_interval_s: float = 1.0
    stale_after_s: float = 3.0
    read_only: bool = True  # Always True - no control commands


@dataclass
class StatusSnapshot:
    """Latest parsed status data."""
    source: str  # "REAL" or "SIMULATED"
    connected: bool
    received_at: str | None
    age_ms: int | None
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

    def __init__(self, config: ConnectionConfig) -> None:
        self.config = config
        self._client: BasicServerClient | None = None
        self._snapshot = StatusSnapshot(
            source="SIMULATED",
            connected=False,
            received_at=None,
            age_ms=None,
        )
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._message_count = 0
        self._error_count = 0

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
        """Start real-time status streaming."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop streaming and close connection."""
        self._running = False
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _run_loop(self) -> None:
        """Main loop: heartbeat + receive status messages."""
        config = BasicServerConfig(
            host=self.config.host,
            tcp_port=self.config.tcp_port,
            control_enabled=False,  # Read-only mode
            stale_after_seconds=self.config.stale_after_s,
        )
        client = BasicServerClient(config)

        while self._running:
            try:
                client.connect(timeout_seconds=3.0, read_only=True)
                self._update_snapshot(client, connected=True)
                
                while self._running:
                    # Receive active status messages
                    messages = client.receive_messages(timeout_seconds=0.5)
                    for msg in messages:
                        self._process_message(client, msg)
                    
                    # Send heartbeat every interval
                    time.sleep(self.config.heartbeat_interval_s / 2)
                    heartbeat = client.build_heartbeat()
                    try:
                        client.send_read_only(heartbeat)
                    except ClientStateError:
                        pass  # Heartbeat may not get response, that's OK
                    
                    # Check staleness
                    now = datetime.now(UTC)
                    if client.is_stale(now):
                        self._update_snapshot(client, connected=True, stale=True)
                        break  # Reconnect on next iteration

            except ClientStateError as e:
                self._update_snapshot(client, connected=False, error=str(e))
                time.sleep(1)
            except Exception as e:
                self._update_snapshot(client, connected=False, error=str(e))
                time.sleep(1)

        client.close()

    def _process_message(self, client: BasicServerClient, msg: PatrolMessage) -> None:
        """Parse and store status message."""
        try:
            result = parse_status_message(msg)
            with self._lock:
                self._message_count += 1
                self._update_snapshot_inner(client, result)
        except Exception as e:
            with self._lock:
                self._error_count += 1
                self._snapshot.error_message = f"Parse error: {e}"

    def _update_snapshot(self, client: BasicServerClient, *, connected: bool, 
                         stale: bool = False, error: str = "") -> None:
        with self._lock:
            self._snapshot.connected = connected and not stale
            self._snapshot.source = "REAL" if connected and not stale else "SIMULATED"
            self._snapshot.received_at = datetime.now(UTC).isoformat() if connected else None
            self._snapshot.error_message = error
            if connected and client._last_received_at:
                age = (datetime.now(UTC) - client._last_received_at).total_seconds() * 1000
                self._snapshot.age_ms = int(age)

    def _update_snapshot_inner(self, client: BasicServerClient, result: StatusResult) -> None:
        """Update snapshot with parsed status data."""
        self._snapshot.source = "REAL"
        self._snapshot.connected = True
        self._snapshot.received_at = datetime.now(UTC).isoformat()
        
        data = result.data
        if result.status_type == "basic_status":
            self._snapshot.basic = data
        elif result.status_type == "motion_status":
            self._snapshot.motion = data
        elif result.status_type == "device_status":
            self._snapshot.device = data
        elif result.status_type == "error_list":
            self._snapshot.errors = data.get("errors", [])
        elif result.status_type == "nav_status":
            self._snapshot.nav_status = data
        elif result.status_type == "position":
            self._snapshot.position = data
        elif result.status_type == "perception":
            self._snapshot.perception = data
        
        # Calculate age
        if client._last_received_at:
            age = (datetime.now(UTC) - client._last_received_at).total_seconds() * 1000
            self._snapshot.age_ms = int(age)

    def get_status_payload(self) -> dict[str, Any]:
        """Get status payload for dashboard API."""
        with self._lock:
            snap = self._snapshot
            return {
                "source": snap.source,
                "connected": snap.connected,
                "control_enabled": False,
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
            }
