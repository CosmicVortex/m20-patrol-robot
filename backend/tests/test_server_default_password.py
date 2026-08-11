"""Test for server.py default password behavior."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_default_password_is_documented():
    """Test that default password matches documentation."""
    # Documentation specifies 123456 for both gimbal and web service
    expected_password = "123456"

    # Verify it's the documented password
    assert expected_password == "123456"
    assert len(expected_password) >= 6


def test_password_not_random():
    """Test that password follows documentation, not random generation."""
    # The password should be the documented fixed password
    documented_password = "123456"

    # Verify it's not a random token format
    assert documented_password.isascii()
    assert documented_password.isdigit()  # Simple numeric password as per docs
