"""Configuration loader for M20 Web service."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WebServiceConfig:
    """Configuration for the M20 Web service."""
    host: str = "127.0.0.1"
    port: int = 8080
    aos_host: str = ""
    aos_port: int = 30001
    runtime_mode: str = "simulated"
    read_only_mode: bool = True
    control_enabled: bool = False
    telemetry_tx_enabled: bool = False
    telemetry_receive_enabled: bool = True
    stale_after_s: float = 3.0
    session_ttl_s: int = 1800
    auth_enabled: bool = True
    allow_anonymous: bool = False
    manifest_path: str = ""
    static_root: str = ""
    auth_db_path: str = ""

    def __post_init__(self) -> None:
        if self.runtime_mode not in {"simulated", "realtime", "realtime_readonly"}:
            raise ValueError("runtime_mode must be simulated, realtime, or realtime_readonly")
        if self.stale_after_s <= 0:
            raise ValueError("stale_after_s must be positive")
        if self.session_ttl_s <= 0:
            raise ValueError("session_ttl_s must be positive")
        if self.telemetry_tx_enabled:
            raise ValueError("telemetry transmission is disabled in this release")
        if not self.read_only_mode or self.control_enabled:
            raise ValueError("service requires read_only_mode=true and control_enabled=false")


class ConfigLoader:
    """Loads configuration from manifest JSON file."""

    DEFAULT_MANIFEST = "deploy/readonly-manifest.json"

    @classmethod
    def load(cls, manifest_path: Optional[str] = None) -> WebServiceConfig:
        path = manifest_path or cls.DEFAULT_MANIFEST
        config_path = Path(path)

        if not config_path.is_file():
            raise FileNotFoundError(f"required manifest not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls._parse(data, str(config_path))

    @classmethod
    def _parse(cls, data: dict[str, Any], manifest_path: str) -> WebServiceConfig:
        manifest = Path(manifest_path).resolve()
        release_root = manifest.parent.parent
        targets = data.get("targets", {})
        ports = data.get("ports", {})
        return WebServiceConfig(
            host=data.get("host", data.get("web_bind_host", "127.0.0.1")),
            port=data.get("port", ports.get("web", 8080)),
            aos_host=data.get("aos_host", targets.get("aos_host", "")),
            aos_port=data.get("aos_port", ports.get("aos_tcp", 30001)),
            runtime_mode=data.get("runtime_mode", "simulated"),
            read_only_mode=data.get("read_only_mode", True),
            control_enabled=data.get("control_enabled", False),
            telemetry_tx_enabled=data.get("telemetry_tx_enabled", False),
            telemetry_receive_enabled=data.get("telemetry_receive_enabled", data.get("telemetry_rx_enabled", True)),
            stale_after_s=data.get("stale_after_s", data.get("stale_after_seconds", 3.0)),
            session_ttl_s=data.get("session_ttl_s", 1800),
            auth_enabled=data.get("auth_enabled", True),
            allow_anonymous=data.get("allow_anonymous", False),
            manifest_path=manifest_path,
            static_root=data.get("static_root", str(release_root / "docs" / "website")),
            auth_db_path=data.get("auth_db_path", str(release_root / "var" / "m20_auth.db")),
        )
