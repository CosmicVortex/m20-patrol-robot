"""basic_server TCP client primitives for the user-confirmed M20 V0.1.0 protocol.

The client can build read-only requests and maintain transport state. Network I/O
is explicit: callers must call connect/send/receive themselves. Navigation or any
other control request is refused unless control_enabled is explicitly configured.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
# Python 3.8 compatibility: UTC was added in Python 3.11
try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc
from collections import deque
from ipaddress import IPv4Address
import socket
from typing import Final, Deque

from backend.app.protocol.frame import FrameCodec, IncrementalDecoder, m20_v010_layout
from backend.app.protocol.messages import ASDUFormat, decode_patrol_message, encode_patrol_message
from backend.app.protocol.messages import PatrolMessage


_HEARTBEAT: Final[tuple[int, int]] = (100, 100)
_LOCATION_QUERY: Final[tuple[int, int]] = (1007, 2)
_NAVIGATION_PERCEPTION_QUERY: Final[tuple[int, int]] = (2002, 1)


class ClientStateError(RuntimeError):
    """Raised when a request conflicts with configured client safety state."""


@dataclass(frozen=True)
class DeploymentEvidence:
    evidence_id: str
    subject: str
    approved: bool

    def __post_init__(self) -> None:
        if not self.evidence_id.strip() or not self.subject.strip():
            raise ValueError("evidence id and subject are required")
        if type(self.approved) is not bool:
            raise ValueError("evidence approval must be boolean")


@dataclass(frozen=True)
class BasicServerConfig:
    """Validated configuration for the documented basic_server TCP endpoint."""

    host: str
    tcp_port: int = 30001
    control_enabled: bool = False
    stale_after_seconds: float = 3.0
    protocol_evidence: DeploymentEvidence | None = None
    firmware_evidence: DeploymentEvidence | None = None
    permission_evidence: DeploymentEvidence | None = None

    def __post_init__(self) -> None:
        try:
            address = IPv4Address(self.host)
        except ValueError as error:
            raise ValueError("host must be a documented approved IPv4 address") from error
        if not address.is_private or address.is_loopback or address.is_multicast or address.is_unspecified:
            raise ValueError("host must be a private non-loopback unicast IPv4 address")
        if type(self.tcp_port) is not int or not 1 <= self.tcp_port <= 65535:
            raise ValueError("tcp_port must be an integer from 1 to 65535")
        if type(self.control_enabled) is not bool:
            raise ValueError("control_enabled must be boolean")
        if type(self.stale_after_seconds) not in (int, float) or self.stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")


class BasicServerClient:
    """State holder and documented request builder; no implicit device I/O."""

    def __init__(self, config: BasicServerConfig) -> None:
        self.config = config
        self._last_received_at: datetime | None = None
        self._codec = FrameCodec(m20_v010_layout(), max_payload_size=65535)
        self._decoder = IncrementalDecoder(self._codec)
        self._socket: socket.socket | None = None
        self._next_message_id = 0
        self._inbox: Deque[PatrolMessage] = deque()

    @staticmethod
    def _now_text() -> str:
        return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")

    def build_heartbeat(self) -> PatrolMessage:
        return PatrolMessage(*_HEARTBEAT, self._now_text(), {})

    def build_location_query(self) -> PatrolMessage:
        return PatrolMessage(*_LOCATION_QUERY, self._now_text(), {})

    def build_navigation_perception_query(self) -> PatrolMessage:
        return PatrolMessage(*_NAVIGATION_PERCEPTION_QUERY, self._now_text(), {})

    def require_control_permission(self, message: PatrolMessage) -> None:
        if not self.config.control_enabled:
            raise ClientStateError("control is disabled by configuration")
        if (message.message_type, message.command) in (_HEARTBEAT, _LOCATION_QUERY, _NAVIGATION_PERCEPTION_QUERY):
            return
        raise ClientStateError("control request requires navigation safety interlock")

    def record_received_at(self, received_at: datetime) -> None:
        if received_at.tzinfo is None:
            raise ValueError("received_at must include timezone")
        self._last_received_at = received_at.astimezone(UTC)

    def is_stale(self, now: datetime) -> bool:
        if now.tzinfo is None:
            raise ValueError("now must include timezone")
        if self._last_received_at is None:
            return True
        elapsed = (now.astimezone(UTC) - self._last_received_at).total_seconds()
        return elapsed >= self.config.stale_after_seconds

    def connect(self, *, timeout_seconds: float = 3.0, read_only: bool = False) -> None:
        """Connect only to the configured, validated basic_server TCP endpoint.

        V1.2.1:
        - control_enabled=True allows full control with evidence
        - read_only=True allows status subscription only (no control)
        - Default: raises error if control is disabled
        """
        if self._socket is not None:
            raise ClientStateError("client is already connected")

        # Read-only mode: allow connection for status subscription only
        if read_only:
            if type(timeout_seconds) not in (int, float) or timeout_seconds <= 0:
                raise ValueError("timeout_seconds must be positive")
            connection = socket.create_connection((self.config.host, self.config.tcp_port), timeout_seconds)
            connection.settimeout(timeout_seconds)
            self._socket = connection
            return
        # Full control mode: requires evidence and authorization
        if not self.config.control_enabled:
            raise ClientStateError("control is disabled; cannot connect to real device")
        if not all(
            evidence is not None
            for evidence in (
                self.config.protocol_evidence,
                self.config.firmware_evidence,
                self.config.permission_evidence,
            )
        ):
            raise ClientStateError("real connection requires protocol, firmware, and permission evidence")
        evidence = (
            self.config.protocol_evidence,
            self.config.firmware_evidence,
            self.config.permission_evidence,
        )
        if any(item is None or not item.approved or item.subject != self.config.host for item in evidence):
            raise ClientStateError("real connection evidence is not approved for the configured host")
        if type(timeout_seconds) not in (int, float) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        connection = socket.create_connection((self.config.host, self.config.tcp_port), timeout_seconds)
        connection.settimeout(timeout_seconds)
        self._socket = connection

    def connect_for_test(self, address: tuple[str, int]) -> None:
        """Test-only loopback seam; production callers must use connect()."""
        host, port = address
        if host != "127.0.0.1" or type(port) is not int:
            raise ValueError("test connection requires loopback endpoint")
        if self._socket is not None:
            raise ClientStateError("client is already connected")
        self._socket = socket.create_connection(address, 1)
        self._socket.settimeout(1)

    def send_read_only(self, message: PatrolMessage) -> PatrolMessage:
        if (message.message_type, message.command) not in (_HEARTBEAT, _LOCATION_QUERY, _NAVIGATION_PERCEPTION_QUERY):
            raise ClientStateError("only documented read-only messages may use send_read_only")
        frame_id = self._send(message)
        deadline = datetime.now(UTC).timestamp() + 3
        while datetime.now(UTC).timestamp() < deadline:
            response: PatrolMessage | None = None
            remaining = max(0.05, deadline - datetime.now(UTC).timestamp())
            for received in self._receive_from_socket(timeout_seconds=remaining):
                # V1.2.1: match by message_id for request/response correlation
                if response is None and received.message_id == frame_id:
                    response = received
                else:
                    self._inbox.append(received)
            if response is not None:
                return response
        raise ClientStateError(f"no response for message_id={frame_id}")

    def receive_messages(self, *, timeout_seconds: float) -> list[PatrolMessage]:
        if self._inbox:
            messages = list(self._inbox)
            self._inbox.clear()
            return messages
        return self._receive_from_socket(timeout_seconds=timeout_seconds)

    def _receive_from_socket(self, *, timeout_seconds: float) -> list[PatrolMessage]:
        connection = self._require_socket()
        connection.settimeout(timeout_seconds)
        data = connection.recv(65536)
        if not data:
            raise ClientStateError("basic_server closed TCP connection")
        messages = [decode_patrol_message(frame.payload, ASDUFormat(frame.flags)) for frame in self._decoder.feed(data)]
        self.record_received_at(datetime.now(UTC))
        return messages

    def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        self._decoder.reset()
        self._inbox.clear()

    def _send(self, message: PatrolMessage) -> int:
        connection = self._require_socket()
        message_id = self._next_message_id
        self._next_message_id = (self._next_message_id + 1) & 0xFFFF
        payload = encode_patrol_message(message, ASDUFormat.JSON)
        connection.sendall(self._codec.encode(message_id=message_id, payload=payload, flags=ASDUFormat.JSON.value))
        # Attach message_id back to message for correlation
        return message_id

    def _require_socket(self) -> socket.socket:
        if self._socket is None:
            raise ClientStateError("client is not connected")
        return self._socket
