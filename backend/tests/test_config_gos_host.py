"""Test for config.py gos_host support."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.config import ConfigLoader, WebServiceConfig


def test_config_loads_gos_host():
    """Test that config loader reads gos_host from manifest."""
    import tempfile
    import json

    manifest_data = {
        "targets": {
            "aos_host": "10.21.31.103",
            "nos_host": "10.21.31.106",
            "gos_host": "10.21.31.104",
        },
        "ports": {
            "web": 8080,
            "aos_tcp": 30001,
        },
        "runtime_mode": "realtime_readonly",
        "read_only_mode": True,
        "control_enabled": False,
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(manifest_data, f)
        f.flush()
        manifest_path = f.name

    try:
        config = ConfigLoader.load(manifest_path)
        assert config.aos_host == "10.21.31.103"
        assert config.nos_host == "10.21.31.106"
        assert config.gos_host == "10.21.31.104"
    finally:
        import os
        os.unlink(manifest_path)


def test_config_gos_host_defaults_to_empty():
    """Test that config defaults gos_host to empty if not provided."""
    config = WebServiceConfig()
    assert config.gos_host == ""


def test_config_loads_nested_gimbal_target():
    """Test that manifest target metadata reaches the gimbal configuration."""
    import json
    import tempfile

    manifest_data = {
        "targets": {
            "gimbal_host": "192.168.1.108",
            "gimbal_username": "admin",
            "gimbal_password": "test_password",
        },
        "runtime_mode": "realtime_readonly",
        "read_only_mode": True,
        "control_enabled": False,
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as file:
        json.dump(manifest_data, file)
        manifest_path = file.name

    try:
        config = ConfigLoader.load(manifest_path)
        assert config.gimbal_host == "192.168.1.108"
        assert config.gimbal_username == "admin"
        assert config.gimbal_password == "test_password"
    finally:
        import os
        os.unlink(manifest_path)
