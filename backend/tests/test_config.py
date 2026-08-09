"""Tests for configuration loader."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "backend")

from app.config import ConfigLoader, WebServiceConfig


class TestConfigLoader:
    """Tests for ConfigLoader."""

    def test_load_defaults(self, tmp_path):
        config = ConfigLoader.load(str(tmp_path / "missing.json"))
        assert config.host == "127.0.0.1"
        assert config.port == 8080
        assert config.runtime_mode == "simulated"
        assert config.read_only_mode is True
        assert config.control_enabled is False

    def test_load_from_file(self, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({
            "host": "0.0.0.0",
            "port": 9000,
            "aos_host": "10.21.31.103",
            "aos_port": 30001,
            "runtime_mode": "realtime_readonly",
            "read_only_mode": True,
            "control_enabled": False,
            "session_ttl_s": 3600,
        }))

        config = ConfigLoader.load(str(manifest))
        assert config.host == "0.0.0.0"
        assert config.port == 9000
        assert config.aos_host == "10.21.31.103"
        assert config.session_ttl_s == 3600

    def test_invalid_runtime_mode(self, tmp_path):
        manifest = tmp_path / "bad.json"
        manifest.write_text(json.dumps({"runtime_mode": "invalid"}))

        with pytest.raises(ValueError, match="runtime_mode"):
            ConfigLoader.load(str(manifest))

    def test_invalid_stale_after(self, tmp_path):
        manifest = tmp_path / "bad.json"
        manifest.write_text(json.dumps({"stale_after_s": -1}))

        with pytest.raises(ValueError, match="stale_after_s"):
            ConfigLoader.load(str(manifest))

    def test_control_disabled_by_default(self):
        config = WebServiceConfig()
        assert config.control_enabled is False
        assert config.read_only_mode is True
