"""Tests for persistent authentication store.

Tests PBKDF2 password hashing, session management, and user operations.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, "backend")

from app.auth.store import AuthUser, AuthenticationError, Session, UserStore


class TestUserStore:
    """Tests for UserStore."""

    @pytest.fixture
    def store(self, tmp_path):
        return UserStore(tmp_path / "test.db")

    def test_create_user(self, store):
        user = store.create_user("testuser", "testpassword1234", "admin")
        assert user.username == "testuser"
        assert user.role == "admin"
        assert user.enabled is True
        assert user.user_id == 1

    def test_create_user_short_password(self, store):
        with pytest.raises(AuthenticationError, match="6 characters"):
            store.create_user("short", "short", "admin")

    def test_create_user_with_deployment_default_password(self, store):
        user = store.create_user("admin", "123456", "admin")
        assert store.authenticate("admin", "123456") == user

    def test_create_user_empty_username(self, store):
        with pytest.raises(AuthenticationError, match="required"):
            store.create_user("  ", "testpassword1234", "admin")

    def test_create_user_empty_role(self, store):
        with pytest.raises(AuthenticationError, match="required"):
            store.create_user("user", "testpassword1234", "  ")

    def test_create_duplicate_user(self, store):
        store.create_user("unique", "uniquepassword1234", "viewer")
        with pytest.raises(AuthenticationError, match="already exists"):
            store.create_user("unique", "uniquepassword1234", "viewer")

    def test_authenticate_success(self, store):
        store.create_user("authuser", "authpass1234", "admin")
        user = store.authenticate("authuser", "authpass1234")
        assert user.username == "authuser"
        assert user.role == "admin"

    def test_authenticate_wrong_password(self, store):
        store.create_user("wrongpw", "correctpass1234", "viewer")
        with pytest.raises(AuthenticationError, match="invalid credentials"):
            store.authenticate("wrongpw", "wrongpass1234")

    def test_authenticate_nonexistent_user(self, store):
        with pytest.raises(AuthenticationError, match="invalid credentials"):
            store.authenticate("nouser", "nopassword")

    def test_authenticate_disabled_user(self, store):
        user = store.create_user("disableduser", "disabledpass123", "admin")
        # Disable user by updating the database directly
        with store._connect() as db:
            db.execute("UPDATE users SET enabled=0 WHERE id=?", (user.user_id,))
        with pytest.raises(AuthenticationError, match="invalid credentials"):
            store.authenticate("disableduser", "disabledpass123")

    def test_create_session(self, store):
        user = store.create_user("sessionuser", "sessionpass123", "admin")
        session = store.create_session(user)
        assert session.user.username == "sessionuser"
        assert session.token is not None
        assert session.expires_at is not None

    def test_resolve_session(self, store):
        user = store.create_user("resolveuser", "resolvepass123", "admin")
        session = store.create_session(user)
        resolved = store.resolve_session(session.token)
        assert resolved is not None
        assert resolved.user.username == "resolveuser"

    def test_resolve_invalid_token(self, store):
        result = store.resolve_session("invalid-token")
        assert result is None

    def test_resolve_empty_token(self, store):
        result = store.resolve_session("")
        assert result is None

    def test_resolve_expired_session(self, store):
        short_store = UserStore(store.path, session_ttl_s=1)
        user = short_store.create_user("expireuser", "expirepass123", "admin")
        session = short_store.create_session(user)
        import time
        time.sleep(1.1)
        result = short_store.resolve_session(session.token)
        assert result is None

    def test_revoke_session(self, store):
        user = store.create_user("revokeuser", "revokepass123", "admin")
        session = store.create_session(user)
        result = store.revoke_session(session.token)
        assert result is True
        # Session should no longer resolve
        assert store.resolve_session(session.token) is None

    def test_revoke_invalid_token(self, store):
        result = store.revoke_session("invalid-token")
        assert result is False

    def test_has_role_admin(self, store):
        user = store.create_user("adminuser", "adminpass123", "admin")
        assert store.has_role(user, ["admin"]) is True
        assert store.has_role(user, ["viewer"]) is False

    def test_has_role_viewer(self, store):
        user = store.create_user("vieweruser", "viewerpass123", "viewer")
        assert store.has_role(user, ["viewer"]) is True
        assert store.has_role(user, ["admin"]) is False
        assert store.has_role(user, ["admin", "viewer"]) is True

    def test_password_hash_format(self, store):
        store.create_user("hashtest", "testpassword123", "admin")
        with store._connect() as db:
            row = db.execute("SELECT password_hash FROM users WHERE username=?", ("hashtest",)).fetchone()
        hash_value = str(row["password_hash"])
        parts = hash_value.split("$")
        assert len(parts) == 4
        assert parts[0] == "pbkdf2_sha256"
        assert parts[1] == "240000"
        assert len(parts[2]) == 32  # 16 bytes hex
        assert len(parts[3]) == 64  # 32 bytes hex

    def test_session_ttl_configurable(self, tmp_path):
        store = UserStore(tmp_path / "ttl.db", session_ttl_s=3600)
        user = store.create_user("ttluser", "ttlpass12345", "admin")
        session = store.create_session(user)
        # Verify session TTL is set correctly
        with store._connect() as db:
            row = db.execute("SELECT expires_at FROM sessions WHERE user_id=?", (user.user_id,)).fetchone()
        assert row is not None

    def test_invalid_session_ttl(self, tmp_path):
        with pytest.raises(ValueError, match="positive integer"):
            UserStore(tmp_path / "bad.db", session_ttl_s=0)

    def test_invalid_negative_session_ttl(self, tmp_path):
        with pytest.raises(ValueError, match="positive integer"):
            UserStore(tmp_path / "bad.db", session_ttl_s=-1)

    def test_create_user_whitespace_trimmed(self, store):
        user = store.create_user("  spaced  ", "testpassword123", "  admin  ")
        assert user.username == "spaced"
        assert user.role == "admin"
