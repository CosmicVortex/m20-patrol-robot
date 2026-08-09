"""Tests for authentication middleware."""

from __future__ import annotations

import io
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "backend")

from app.auth.middleware import AuthMiddleware, AuthRequiredError
from app.auth.store import AuthUser, Session, UserStore


class FakeHandler:
    """Minimal fake HTTP handler for testing."""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.cookies_sent: list[str] = []

    def get_header(self, name: str) -> str | None:
        return self.headers.get(name)

    def send_header(self, name: str, value: str) -> None:
        self.cookies_sent.append(f"{name}: {value}")


class TestAuthMiddleware:
    """Tests for AuthMiddleware."""

    @pytest.fixture
    def store(self, tmp_path):
        return UserStore(tmp_path / "test.db")

    @pytest.fixture
    def user(self, store):
        return store.create_user("testuser", "testpassword123", "admin")

    @pytest.fixture
    def session(self, store, user):
        return store.create_session(user)

    @pytest.fixture
    def middleware(self, store):
        return AuthMiddleware(store, require_role=["admin"])

    def test_extract_token_from_header(self, middleware):
        handler = FakeHandler()
        handler.headers["X-M20-Token"] = "test-token-123"

        token = middleware._extract_token(handler)
        assert token == "test-token-123"

    def test_extract_token_from_bearer(self, middleware):
        handler = FakeHandler()
        handler.headers["Authorization"] = "Bearer my-token-456"

        token = middleware._extract_token(handler)
        assert token == "my-token-456"

    def test_extract_token_from_basic(self, store, middleware):
        user = store.create_user("basicuser", "basicpass1234", "viewer")
        import base64
        credentials = base64.b64encode(b"basicuser:basicpass1234").decode()

        handler = FakeHandler()
        handler.headers["Authorization"] = f"Basic {credentials}"

        token = middleware._extract_token(handler)
        assert token is not None

    def test_extract_token_missing(self, middleware):
        handler = FakeHandler()
        token = middleware._extract_token(handler)
        assert token is None

    def test_authenticate_valid_token(self, middleware, session):
        handler = FakeHandler()
        handler.headers["X-M20-Token"] = session.token

        result = middleware.authenticate(handler)
        assert result is not None
        assert result.user.username == "testuser"
        assert result.role == "admin"

    def test_authenticate_missing_token(self, middleware):
        handler = FakeHandler()

        with pytest.raises(AuthRequiredError):
            middleware.authenticate(handler)

    def test_authenticate_invalid_token(self, middleware):
        handler = FakeHandler()
        handler.headers["X-M20-Token"] = "invalid-token"

        with pytest.raises(AuthRequiredError):
            middleware.authenticate(handler)

    def test_authenticate_expired_token(self, store, middleware):
        user = store.create_user("expireuser", "expirepass123", "admin")
        # Create session with very short TTL
        expired_store = UserStore(store.path, session_ttl_s=1)
        session = expired_store.create_session(user)

        # Wait for session to expire
        import time
        time.sleep(1.1)

        handler = FakeHandler()
        handler.headers["X-M20-Token"] = session.token

        # Expect authentication to fail due to expired token
        with pytest.raises(AuthRequiredError):
            middleware.authenticate(handler)

    def test_authenticate_insufficient_role(self, store):
        viewer_store = UserStore(store.path)
        viewer = viewer_store.create_user("vieweruser", "viewerpass123", "viewer")
        viewer_session = viewer_store.create_session(viewer)

        admin_middleware = AuthMiddleware(viewer_store, require_role=["admin"])

        handler = FakeHandler()
        handler.headers["X-M20-Token"] = viewer_session.token

        with pytest.raises(AuthRequiredError):
            admin_middleware.authenticate(handler)

    def test_set_session_cookie(self, middleware, session):
        handler = FakeHandler()
        middleware.set_session_cookie(handler, session)

        assert len(handler.cookies_sent) == 1
        assert "m20_session=" in handler.cookies_sent[0]
        assert "HttpOnly" in handler.cookies_sent[0]
        assert "SameSite=Lax" in handler.cookies_sent[0]

    def test_revoke_session_cookie(self, middleware):
        handler = FakeHandler()
        middleware.revoke_session_cookie(handler)

        assert len(handler.cookies_sent) == 1
        assert "m20_session=;" in handler.cookies_sent[0]

    def test_allow_anonymous(self, store):
        middleware = AuthMiddleware(store, allow_anonymous=True)
        handler = FakeHandler()

        result = middleware.authenticate(handler)
        assert result is None
