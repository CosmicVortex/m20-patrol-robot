"""HTTP authentication middleware and helpers.

This module provides request-level authentication primitives that sit above
the persistence layer in :py:mod:`backend.app.auth.store`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
from http.cookies import SimpleCookie
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from http.server import BaseHTTPRequestHandler
from typing import Optional

try:
    from datetime import UTC
except ImportError:  # Python 3.8
    UTC = timezone.utc

from backend.app.auth.store import AuthUser, AuthenticationError, Session, UserStore

logger = logging.getLogger(__name__)

_TOKEN_HEADER = "X-M20-Token"
_BASIC_REALM = "m20-patrol"


@dataclass(frozen=True)
class AuthResult:
    user: AuthUser
    session: Session
    role: str


class AuthRequiredError(AuthenticationError):
    """Raised when authentication or authorization is missing or invalid."""


class AuthMiddleware:
    """Extracts and validates authentication state from HTTP requests."""

    def __init__(
        self,
        store: UserStore,
        *,
        token_header: str = _TOKEN_HEADER,
        require_role: list[str] | None = None,
        allow_anonymous: bool = False,
    ) -> None:
        self.store = store
        self.token_header = token_header
        self.required_roles = set(require_role or [])
        self.allow_anonymous = allow_anonymous

    def _extract_token(self, handler: BaseHTTPRequestHandler) -> Optional[str]:
        """Extract token from header, query string, or cookie."""
        # Check custom header first
        header_value = handler.headers.get(self.token_header)
        if header_value:
            logger.debug("从 X-M20-Token 头提取令牌")
            return header_value.strip()

        # Check Authorization: Bearer ***
        auth_header = handler.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            logger.debug("从 Authorization: Bearer 提取令牌")
            return auth_header[7:].strip()

        # Check Authorization: Basic (username:password fallback)
        if auth_header.lower().startswith("basic "):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                username, _, password = decoded.partition(":")
                if username and password:
                    try:
                        user = self.store.authenticate(username, password)
                        session = self.store.create_session(user)
                        return session.token
                    except AuthenticationError:
                        pass
            except Exception:
                pass

        cookie = SimpleCookie()
        cookie.load(handler.headers.get("Cookie", ""))
        morsel = cookie.get("m20_session")
        if morsel is not None:
            return morsel.value

        return None

    def authenticate(self, handler: BaseHTTPRequestHandler) -> Optional[AuthResult]:
        """Extract and validate authentication. Returns AuthResult or None."""
        if self.allow_anonymous:
            return None

        token = self._extract_token(handler)
        if not token:
            if self.allow_anonymous:
                return None
            raise AuthRequiredError("missing authentication token")

        session = self.store.resolve_session(token)
        if not session:
            raise AuthRequiredError("invalid or expired session")

        if self.required_roles and not self.store.has_role(session.user, self.required_roles):
            raise AuthRequiredError("insufficient role")

        return AuthResult(
            user=session.user,
            session=session,
            role=session.user.role,
        )

    def set_session_cookie(self, handler: BaseHTTPRequestHandler, session: Session) -> None:
        """Set session token as HTTP cookie."""
        expiry = datetime.fromisoformat(session.expires_at)
        handler.send_header(
            "Set-Cookie",
            f"m20_session={session.token}; "
            f"Expires={expiry.strftime('%a, %d %b %Y %H:%M:%S GMT')}; "
            f"HttpOnly; SameSite=Lax; Path=/",
        )

    def revoke_session_cookie(self, handler: BaseHTTPRequestHandler) -> None:
        """Clear session cookie."""
        handler.send_header(
            "Set-Cookie",
            "m20_session=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/",
        )
