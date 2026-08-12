"""Persistent authentication primitives for the M20 Web service.

This module is intentionally independent of HTTP and robot I/O. It stores only
PBKDF2 password hashes and SHA-256 hashes of short-lived session tokens.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Sequence, Union

try:
    from datetime import UTC
except ImportError:  # Python 3.8
    UTC = timezone.utc

_PASSWORD_SCHEME = "pbkdf2_sha256"
_PASSWORD_ITERATIONS = 240_000
_SESSION_BYTES = 32


class AuthenticationError(ValueError):
    """Raised for invalid credentials or malformed authentication data."""


@dataclass(frozen=True)
class AuthUser:
    user_id: int
    username: str
    role: str
    enabled: bool


@dataclass(frozen=True)
class Session:
    token: str
    user: AuthUser
    expires_at: str


class UserStore:
    """SQLite-backed user and session store."""

    def __init__(self, path: Union[str, Path], *, session_ttl_s: int = 1800) -> None:
        if type(session_ttl_s) is not int or session_ttl_s <= 0:
            raise ValueError("session_ttl_s must be a positive integer")
        self.path = str(path)
        self.session_ttl_s = session_ttl_s
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def _initialize(self) -> None:
        parent = Path(self.path).parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    expires_at TEXT NOT NULL,
                    revoked_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
                """
            )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _hash_password(password: str, *, salt: Optional[bytes] = None) -> str:
        if not isinstance(password, str) or len(password) < 6:
            raise AuthenticationError("password must contain at least 6 characters")
        salt = salt or secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, _PASSWORD_ITERATIONS
        )
        return "$".join(
            (
                _PASSWORD_SCHEME,
                str(_PASSWORD_ITERATIONS),
                salt.hex(),
                digest.hex(),
            )
        )

    @staticmethod
    def _verify_password(password: str, encoded: str) -> bool:
        try:
            scheme, iterations_text, salt_hex, digest_hex = encoded.split("$", 3)
            if scheme != _PASSWORD_SCHEME:
                return False
            iterations = int(iterations_text)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(digest_hex)
        except (ValueError, TypeError):
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations
        )
        return hmac.compare_digest(actual, expected)

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> AuthUser:
        return AuthUser(
            user_id=int(row["id"]),
            username=str(row["username"]),
            role=str(row["role"]),
            enabled=bool(row["enabled"]),
        )

    def create_user(self, username: str, password: str, role: str) -> AuthUser:
        username = username.strip()
        role = role.strip()
        if not username or not role:
            raise AuthenticationError("username and role are required")
        password_hash = self._hash_password(password)
        with self._connect() as db:
            try:
                cursor = db.execute(
                    "INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)",
                    (username, password_hash, role, self._now().isoformat()),
                )
            except sqlite3.IntegrityError as error:
                raise AuthenticationError("username already exists") from error
            row = db.execute("SELECT * FROM users WHERE id=?", (cursor.lastrowid,)).fetchone()
        assert row is not None
        return self._row_to_user(row)

    def authenticate(self, username: str, password: str) -> AuthUser:
        with self._connect() as db:
            row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if row is None or not bool(row["enabled"]):
            raise AuthenticationError("invalid credentials")
        if not self._verify_password(password, str(row["password_hash"])):
            raise AuthenticationError("invalid credentials")
        return self._row_to_user(row)

    def create_session(self, user: AuthUser) -> Session:
        raw_token = secrets.token_urlsafe(_SESSION_BYTES)
        token_hash = hashlib.sha256(raw_token.encode("ascii")).hexdigest()
        expires = self._now() + timedelta(seconds=self.session_ttl_s)
        with self._connect() as db:
            db.execute(
                "INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)",
                (token_hash, user.user_id, expires.isoformat()),
            )
        return Session(token=raw_token, user=user, expires_at=expires.isoformat())

    def resolve_session(self, token: str) -> Optional[Session]:
        if not isinstance(token, str) or not token:
            return None
        token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
        now = self._now()
        with self._connect() as db:
            row = db.execute(
                """SELECT s.expires_at, u.* FROM sessions s JOIN users u ON u.id=s.user_id
                   WHERE s.token_hash=? AND s.revoked_at IS NULL""",
                (token_hash,),
            ).fetchone()
        if row is None or not bool(row["enabled"]):
            return None
        try:
            expires = datetime.fromisoformat(str(row["expires_at"]))
        except ValueError:
            return None
        if expires <= now:
            return None
        return Session(token=token, user=self._row_to_user(row), expires_at=expires.isoformat())

    def revoke_session(self, token: str) -> bool:
        if not isinstance(token, str) or not token:
            return False
        token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
        with self._connect() as db:
            result = db.execute(
                "UPDATE sessions SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL",
                (self._now().isoformat(), token_hash),
            )
        return result.rowcount == 1

    def has_role(self, user: AuthUser, allowed: Sequence[str]) -> bool:
        return user.enabled and user.role in set(allowed)
