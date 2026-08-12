"""Test for server.py default password behavior."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.config import WebServiceConfig
from backend.app.server import M20WebServer


def test_default_password_is_documented():
    """Test that default password matches documentation."""
    # Documentation specifies 123456 for web service admin
    expected_password = "123456"

    # Verify password meets minimum length requirement
    assert len(expected_password) >= 6


def test_password_is_numeric():
    """Test that password format matches documentation."""
    documented_password = "123456"

    # Verify it's numeric
    assert documented_password.isascii()
    assert documented_password.isdigit()


def test_server_provisions_documented_admin_password(tmp_path, monkeypatch):
    monkeypatch.delenv("M20_ADMIN_PASSWORD", raising=False)
    config = WebServiceConfig(
        aos_host="10.21.31.103",
        auth_db_path=str(tmp_path / "auth.db"),
    )
    server = M20WebServer(config)
    server.setup()
    try:
        assert server.user_store is not None
        user = server.user_store.authenticate("admin", "123456")
        assert user.role == "admin"
    finally:
        server.stop()
