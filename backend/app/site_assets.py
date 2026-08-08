"""Site-specific deployment assets with fail-closed evidence validation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class StrEnum(str, Enum):
    pass


class CameraSourceKind(StrEnum):
    ROBOT_BODY = "robot_body"
    SUER_SECURITY = "suer_security"


@dataclass(frozen=True)
class SiteMapAsset:
    site_id: str
    map_identity: str
    package_sha256: str
    verified_on: str

    def __post_init__(self) -> None:
        if not self.site_id.strip():
            raise ValueError("site_id is required")
        if not self.map_identity.strip() or "REPLACE_WITH" in self.map_identity:
            raise ValueError("map_identity must be a confirmed site map identity")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", self.package_sha256):
            raise ValueError("package_sha256 must be a 64-character SHA-256 hex digest")
        if not self.verified_on.strip():
            raise ValueError("verified_on is required")


@dataclass(frozen=True)
class CameraSource:
    name: str
    kind: CameraSourceKind
    stream_uri: str | None
    verified: bool
    verified_on: str | None
    evidence_id: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("camera name is required")
        if type(self.verified) is not bool:
            raise ValueError("verified must be boolean")
        if self.verified and (
            not self.stream_uri or not self.stream_uri.strip() or
            not self.verified_on or not self.verified_on.strip() or
            not self.evidence_id or not self.evidence_id.strip()
        ):
            raise ValueError("a verified camera source requires URI and verification date")
        if self.kind is CameraSourceKind.SUER_SECURITY and self.verified:
            raise ValueError("suer security source is reserved for a later adapter")
        if self.verified is False and self.verified_on is not None:
            raise ValueError("unverified camera source cannot have a verification date")

    @property
    def is_available(self) -> bool:
        return self.verified and bool(self.stream_uri and self.verified_on)


@dataclass(frozen=True)
class SiteProfile:
    site_id: str
    display_name: str
    map_asset: SiteMapAsset
    cameras: tuple[CameraSource, ...]

    def __post_init__(self) -> None:
        if not self.site_id.strip() or not self.display_name.strip():
            raise ValueError("site identity is required")
        if self.map_asset.site_id != self.site_id:
            raise ValueError("map asset belongs to a different site")
        if any(camera.name == "" for camera in self.cameras):
            raise ValueError("camera names must not be empty")