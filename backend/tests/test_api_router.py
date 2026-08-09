"""Tests for API router."""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "backend")

from app.auth.middleware import AuthMiddleware
from app.auth.store import UserStore
from app.api.router import ApiRouter


class TestApiRouter:
    """Tests for ApiRouter."""

    @pytest.fixture
    def store(self, tmp_path):
        return UserStore(tmp_path / "test.db")

    @pytest.fixture
    def middleware(self, store):
        return AuthMiddleware(store, allow_anonymous=True)

    @pytest.fixture
    def router(self, store, middleware):
        return ApiRouter(store, middleware)

    def test_health_route_exists(self, router):
        """Verify health route is registered."""
        assert "/api/v1/health" in router.HANDLERS

    def test_auth_login_route_exists(self, router):
        """Verify auth login route is registered."""
        assert "/api/v1/auth/login" in router.HANDLERS

    def test_auth_logout_route_exists(self, router):
        """Verify auth logout route is registered."""
        assert "/api/v1/auth/logout" in router.HANDLERS

    def test_auth_me_route_exists(self, router):
        """Verify auth me route is registered."""
        assert "/api/v1/auth/me" in router.HANDLERS

    def test_status_latest_route_exists(self, router):
        """Verify status latest route is registered."""
        assert "/api/v1/status/latest" in router.HANDLERS

    def test_devices_route_exists(self, router):
        """Verify devices route is registered."""
        assert "/api/v1/devices" in router.HANDLERS

    def test_navigation_status_route_exists(self, router):
        """Verify navigation status route is registered."""
        assert "/api/v1/navigation/status" in router.HANDLERS

    def test_navigation_authorize_route_exists(self, router):
        """Verify navigation authorize route is registered."""
        assert "/api/v1/navigation/authorize" in router.HANDLERS

    def test_navigation_tasks_route_exists(self, router):
        """Verify navigation tasks route is registered."""
        assert "/api/v1/navigation/tasks" in router.HANDLERS

    def test_router_creates_with_dependencies(self, router):
        """Verify router is created with proper dependencies."""
        assert router.user_store is not None
        assert router.auth_middleware is not None
