"""Tests for API response formatting."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, "backend")

from app.api.response import ApiFormatter, ApiResponse, StatusCode


class TestApiFormatter:
    """Tests for ApiFormatter."""

    def test_success_with_data(self):
        result = ApiFormatter.success({"key": "value"})
        assert result["status"] == "success"
        assert result["data"] == {"key": "value"}
        assert result["code"] == "ok"
        assert "timestamp" in result

    def test_success_without_data(self):
        result = ApiFormatter.success()
        assert result["status"] == "success"
        assert result["data"] is None

    def test_error(self):
        result = ApiFormatter.error("Something went wrong", "test_error")
        assert result["status"] == "error"
        assert result["error"] == "Something went wrong"
        assert result["code"] == "test_error"
        assert "timestamp" in result

    def test_send_json_response(self):
        handler = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = MagicMock()

        ApiFormatter.send_json(handler, 200, {"status": "ok"})

        handler.send_response.assert_called_once_with(200)
        header_values = [call[0][1] for call in handler.send_header.call_args_list]
        assert "application/json; charset=utf-8" in header_values
        assert "nosniff" in header_values

    def test_send_error_response(self):
        handler = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = MagicMock()

        ApiFormatter.send_error(handler, 401, "Unauthorized", "unauthorized")

        handler.send_response.assert_called_once_with(401)
