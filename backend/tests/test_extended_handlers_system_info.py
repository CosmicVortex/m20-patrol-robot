"""Test for extended_handlers system info endpoint."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.api.extended_handlers import SystemInfoHandler


def test_system_info_returns_gos_host_from_config():
    """Test that system info returns configured gos_host, not hardcoded."""
    handler = SystemInfoHandler.__new__(SystemInfoHandler)
    handler.config = MagicMock()
    handler.config.aos_host = "10.21.31.103"
    handler.config.aos_port = 30001
    handler.config.nos_host = "10.21.31.106"
    handler.config.gos_host = "10.21.31.104"
    handler.config.runtime_mode = "realtime_readonly"
    handler.config.auth_enabled = True
    handler.gimbal_adapter = None

    # Mock response methods
    handler.send_json_response = MagicMock()

    # Call do_GET
    handler.path = "/api/v1/system/info"
    handler._authenticate = MagicMock(return_value=None)
    handler.config.allow_anonymous = True

    handler.do_GET()

    # Verify response
    assert handler.send_json_response.called
    response_args = handler.send_json_response.call_args
    data = response_args[0][1]
    assert data["hos"]["gos_host"] == "10.21.31.104"
    assert data["hos"]["nos_host"] == "10.21.31.106"
