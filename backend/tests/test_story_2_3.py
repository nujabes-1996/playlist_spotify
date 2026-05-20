"""Tests for Story 2.3: Token Re-Authentication Flow."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# AC1, AC5, AC6 — get_auth_status() branching logic
# ---------------------------------------------------------------------------

class TestGetAuthStatusHasPreviousAuth:
    def test_no_credentials_returns_not_authenticated_no_previous_auth(self):
        """AC5: no credentials → authenticated=False, has_previous_auth=False."""
        from services import spotify as svc
        with patch.object(svc, "_get_spotify_oauth", side_effect=ValueError("not configured")):
            result = svc.get_auth_status()
        assert result == {"authenticated": False, "has_previous_auth": False, "spotify_user_id": None}

    def test_no_cached_token_returns_not_authenticated_no_previous_auth(self):
        """AC5: credentials OK but no token stored → has_previous_auth=False."""
        mock_oauth = MagicMock()
        mock_oauth.get_cached_token.return_value = None
        from services import spotify as svc
        with patch.object(svc, "_get_spotify_oauth", return_value=mock_oauth):
            result = svc.get_auth_status()
        assert result == {"authenticated": False, "has_previous_auth": False, "spotify_user_id": None}

    def test_validate_token_returns_none_means_revoked_has_previous_auth_true(self):
        """AC1: token exists but validate_token → None → has_previous_auth=True."""
        mock_oauth = MagicMock()
        mock_oauth.get_cached_token.return_value = {"access_token": "expired"}
        mock_oauth.validate_token.return_value = None
        from services import spotify as svc
        with patch.object(svc, "_get_spotify_oauth", return_value=mock_oauth):
            result = svc.get_auth_status()
        assert result == {"authenticated": False, "has_previous_auth": True, "spotify_user_id": None}

    def test_valid_token_returns_authenticated_with_previous_auth_true(self):
        """AC4: valid token + user.me() → authenticated=True, has_previous_auth=True."""
        mock_oauth = MagicMock()
        mock_oauth.get_cached_token.return_value = {"access_token": "valid_token"}
        mock_oauth.validate_token.return_value = {"access_token": "valid_token"}
        mock_sp = MagicMock()
        mock_sp.me.return_value = {"id": "spotify_user_123"}
        from services import spotify as svc
        with patch.object(svc, "_get_spotify_oauth", return_value=mock_oauth), \
             patch("services.spotify.Spotify", return_value=mock_sp):
            result = svc.get_auth_status()
        assert result == {"authenticated": True, "has_previous_auth": True, "spotify_user_id": "spotify_user_123"}

    def test_network_error_after_token_stored_returns_has_previous_auth_true(self):
        """AC1: token stored but network fails → has_previous_auth=True (show ReauthBanner)."""
        mock_oauth = MagicMock()
        mock_oauth.get_cached_token.return_value = {"access_token": "tok"}
        mock_oauth.validate_token.side_effect = Exception("network error")
        from services import spotify as svc
        with patch.object(svc, "_get_spotify_oauth", return_value=mock_oauth):
            result = svc.get_auth_status()
        assert result == {"authenticated": False, "has_previous_auth": True, "spotify_user_id": None}


# ---------------------------------------------------------------------------
# AC1 — /auth/status endpoint response shape
# ---------------------------------------------------------------------------

class TestAuthStatusEndpoint:
    @pytest.fixture
    def client(self):
        with patch("scheduler.scheduler.start"), patch("scheduler.scheduler.shutdown"):
            from main import app
            return TestClient(app)

    def test_status_endpoint_includes_has_previous_auth_false_when_no_creds(self, client):
        """AC5: endpoint returns has_previous_auth=false when no credentials."""
        from services import spotify as svc
        with patch.object(svc, "get_auth_status", return_value={
            "authenticated": False,
            "has_previous_auth": False,
            "spotify_user_id": None,
        }):
            response = client.get("/api/v1/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["has_previous_auth"] is False
        assert data["spotify_user_id"] is None

    def test_status_endpoint_includes_has_previous_auth_true_when_revoked(self, client):
        """AC1: endpoint returns has_previous_auth=true when token revoked."""
        from services import spotify as svc
        with patch.object(svc, "get_auth_status", return_value={
            "authenticated": False,
            "has_previous_auth": True,
            "spotify_user_id": None,
        }):
            response = client.get("/api/v1/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["has_previous_auth"] is True

    def test_status_endpoint_authenticated_has_previous_auth_true(self, client):
        """AC4: endpoint returns authenticated=true with has_previous_auth=true."""
        from services import spotify as svc
        with patch.object(svc, "get_auth_status", return_value={
            "authenticated": True,
            "has_previous_auth": True,
            "spotify_user_id": "user_abc",
        }):
            response = client.get("/api/v1/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["has_previous_auth"] is True
        assert data["spotify_user_id"] == "user_abc"

    def test_status_response_does_not_leak_token_data(self, client):
        """NFR5: response must not contain access_token, refresh_token, spotify_token_json."""
        from services import spotify as svc
        with patch.object(svc, "get_auth_status", return_value={
            "authenticated": True,
            "has_previous_auth": True,
            "spotify_user_id": "user_abc",
        }):
            response = client.get("/api/v1/auth/status")
        data = response.json()
        assert "access_token" not in data
        assert "refresh_token" not in data
        assert "spotify_token_json" not in data
