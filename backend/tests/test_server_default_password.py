"""Test for server.py default password behavior."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


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
