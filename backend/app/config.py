"""Configuration loader for M20 Web service."""

from __future__ import annotations

import json
import logging
import os
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
    telemetry_tx_enabled: bool = True  # 必须发送心跳保活
    telemetry_receive_enabled: bool = True
    stale_after_s: float = 3.0  # 对应manifest.json中的stale_after_seconds
    session_ttl_s: int = 1800
    auth_enabled: bool = True
    allow_anonymous: bool = False
    allow_real_io: bool = False
    gimbal_host: str = ""
    gimbal_username: str = "admin"
    gimbal_password: str = ""  # 可选，通过环境变量 M20_GIMBAL_PASSWORD 设置
    nos_host: str = ""  # 导航操作员站地址，从 manifest 读取
    gos_host: str = ""  # GOS主机地址，从 manifest 读取
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
        # telemetry_tx_enabled=True is required for heartbeat keepalive
        # 安全约束：禁止同时启用读写控制且不禁用只读模式
        # 允许 read_only_mode=false 且 control_enabled=true（完整控制模式）
        # 允许 read_only_mode=true 且 control_enabled=false（只读模式）
        # 不允许 read_only_mode=false 且 control_enabled=false（无效配置）
        if not self.read_only_mode and not self.control_enabled:
            raise ValueError("service requires control_enabled=true when read_only_mode=false")


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
        def env_text(name: str, default: str) -> str:
            return os.environ.get(name) or default

        def env_int(name: str, default: int) -> int:
            return int(os.environ.get(name) or default)

        def env_bool(name: str, default: bool) -> bool:
            value = os.environ.get(name)
            if value is None:
                return default
            if value.lower() in {"1", "true", "yes", "on"}:
                return True
            if value.lower() in {"0", "false", "no", "off"}:
                return False
            raise ValueError(f"{name} must be boolean")

        return WebServiceConfig(
            host=env_text("M20_WEB_BIND_HOST", data.get("host", data.get("web_bind_host", "127.0.0.1"))),
            port=env_int("M20_WEB_PORT", data.get("port", ports.get("web", 8080))),
            aos_host=env_text("M20_TARGET_HOST", data.get("aos_host", targets.get("aos_host", ""))),
            aos_port=env_int("M20_TARGET_PORT", data.get("aos_port", ports.get("aos_tcp", 30001))),
            nos_host=data.get("nos_host", targets.get("nos_host", "")),
            gos_host=data.get("gos_host", targets.get("gos_host", "")),
            runtime_mode=env_text("M20_RUNTIME_MODE", data.get("runtime_mode", "simulated")),
            read_only_mode=env_bool("M20_READ_ONLY_MODE", data.get("read_only_mode", True)),
            control_enabled=env_bool("M20_CONTROL_ENABLED", data.get("control_enabled", False)),
            telemetry_tx_enabled=env_bool("M20_TELEMETRY_TX_ENABLED", data.get("telemetry_tx_enabled", False)),
            telemetry_receive_enabled=env_bool("M20_TELEMETRY_RX_ENABLED", data.get("telemetry_receive_enabled", data.get("telemetry_rx_enabled", True))),
            stale_after_s=float(os.environ.get("M20_STALE_AFTER_SECONDS") or data.get("stale_after_s", data.get("stale_after_seconds", 3.0))),
            session_ttl_s=data.get("session_ttl_s", 1800),
            auth_enabled=env_bool("M20_AUTH_ENABLED", data.get("auth_enabled", True)),
            allow_anonymous=env_bool("M20_ALLOW_ANONYMOUS", data.get("allow_anonymous", False)),
            allow_real_io=env_bool("M20_ALLOW_REAL_IO", data.get("allow_real_io", False)),
            gimbal_host=data.get("gimbal_host", targets.get("gimbal_host", "")),
            gimbal_username=data.get("gimbal_username", targets.get("gimbal_username", "admin")),
            gimbal_password=os.environ.get("M20_GIMBAL_PASSWORD") or data.get(
                "gimbal_password", targets.get("gimbal_password", "")
            ),
            manifest_path=manifest_path,
            static_root=data.get("static_root", str(release_root / "docs" / "website")),
            auth_db_path=data.get("auth_db_path", str(release_root / "var" / "m20_auth.db")),
        )
