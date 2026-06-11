"""Tests for Story 2.3: Token Re-Authentication Flow.

Re-baselined for Story 10.2: get_auth_status() is now per-user (takes a User and
returns display_name), and GET /auth/status is session-based (no session → unauthenticated;
with a session it reflects the user's token validity).
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from models.user import User


def _user(display_name=None):
    return User(
        id=1, spotify_user_id="u1", client_id="cid", client_secret="csec", display_name=display_name
    )


# ---------------------------------------------------------------------------
# AC1, AC5, AC6 — get_auth_status(user) branching logic
# ---------------------------------------------------------------------------

class TestGetAuthStatusHasPreviousAuth:
    def test_no_credentials_returns_not_authenticated_no_previous_auth(self):
        """AC5: no credentials → authenticated=False, has_previous_auth=False."""
        from services import spotify as svc
        with patch.object(svc, "_get_spotify_oauth", side_effect=ValueError("not configured")):
            result = svc.get_auth_status(_user())
        assert result == {
            "authenticated": False,
            "has_previous_auth": False,
            "spotify_user_id": None,
            "display_name": None,
        }

    def test_no_cached_token_returns_not_authenticated_no_previous_auth(self):
        """AC5: credentials OK but no token stored → has_previous_auth=False."""
        mock_oauth = MagicMock()
        mock_oauth.get_cached_token.return_value = None
        from services import spotify as svc
        with patch.object(svc, "_get_spotify_oauth", return_value=mock_oauth):
            result = svc.get_auth_status(_user())
        assert result == {
            "authenticated": False,
            "has_previous_auth": False,
            "spotify_user_id": None,
            "display_name": None,
        }

    def test_validate_token_returns_none_means_revoked_has_previous_auth_true(self):
        """AC1: token exists but validate_token → None → has_previous_auth=True."""
        mock_oauth = MagicMock()
        mock_oauth.get_cached_token.return_value = {"access_token": "expired"}
        mock_oauth.validate_token.return_value = None
        from services import spotify as svc
        with patch.object(svc, "_get_spotify_oauth", return_value=mock_oauth):
            result = svc.get_auth_status(_user(display_name="Stored"))
        assert result == {
            "authenticated": False,
            "has_previous_auth": True,
            "spotify_user_id": None,
            "display_name": "Stored",
        }

    def test_valid_token_returns_authenticated_with_previous_auth_true(self):
        """AC4: valid token + me() → authenticated=True, live display_name preferred."""
        mock_oauth = MagicMock()
        mock_oauth.get_cached_token.return_value = {"access_token": "valid_token"}
        mock_oauth.validate_token.return_value = {"access_token": "valid_token"}
        mock_sp = MagicMock()
        mock_sp.me.return_value = {"id": "spotify_user_123", "display_name": "Live Name"}
        from services import spotify as svc
        with patch.object(svc, "_get_spotify_oauth", return_value=mock_oauth), \
             patch("services.spotify.Spotify", return_value=mock_sp):
            result = svc.get_auth_status(_user(display_name="Stored"))
        assert result == {
            "authenticated": True,
            "has_previous_auth": True,
            "spotify_user_id": "spotify_user_123",
            "display_name": "Live Name",
        }

    def test_network_error_after_token_stored_returns_has_previous_auth_true(self):
        """AC1: token stored but network fails → has_previous_auth=True (ReauthBanner)."""
        mock_oauth = MagicMock()
        mock_oauth.get_cached_token.return_value = {"access_token": "tok"}
        mock_oauth.validate_token.side_effect = Exception("network error")
        from services import spotify as svc
        with patch.object(svc, "_get_spotify_oauth", return_value=mock_oauth):
            result = svc.get_auth_status(_user(display_name="Stored"))
        assert result == {
            "authenticated": False,
            "has_previous_auth": True,
            "spotify_user_id": None,
            "display_name": "Stored",
        }


# ---------------------------------------------------------------------------
# AC1 / AC6 — /auth/status endpoint is session-based
# ---------------------------------------------------------------------------

class TestAuthStatusEndpoint:
    @pytest.fixture(name="engine")
    def engine_fixture(self):
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        SQLModel.metadata.create_all(engine)
        return engine

    @pytest.fixture(name="session")
    def session_fixture(self, engine):
        with Session(engine) as session:
            yield session

    @pytest.fixture(name="client")
    def client_fixture(self, engine, session):
        app.dependency_overrides[get_session] = lambda: session
        with patch("services.spotify.engine", engine), patch(
            "services.token_manager.engine", engine
        ):
            yield TestClient(app)
        app.dependency_overrides.clear()

    def _login(self, client):
        with patch("services.spotify.SpotifyOAuth") as MockOAuth:
            MockOAuth.return_value.get_authorize_url.return_value = "https://x?state=s"
            client.post("/api/v1/auth/connect", json={"client_id": "cid", "client_secret": "csec"})
            state = MockOAuth.call_args.kwargs["state"]
        with patch("services.spotify.SpotifyOAuth") as MockOAuth, patch(
            "services.spotify.Spotify"
        ) as MockSpotify:
            MockOAuth.return_value.get_access_token.return_value = {
                "access_token": "tok",
                "expires_at": 9999999999,
            }
            MockSpotify.return_value.me.return_value = {"id": "user_abc", "display_name": "Abc"}
            client.get(
                "/api/v1/auth/callback",
                params={"code": "c", "state": state},
                follow_redirects=False,
            )

    def test_no_session_returns_unauthenticated(self, client):
        """AC6: no session user → authenticated=false, has_previous_auth=false."""
        response = client.get("/api/v1/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["has_previous_auth"] is False
        assert data["spotify_user_id"] is None

    def test_status_endpoint_passes_through_revoked_state(self, client):
        """AC1: with a session, the endpoint surfaces a revoked (has_previous_auth) state."""
        from services import spotify as svc
        self._login(client)
        with patch.object(svc, "get_auth_status", return_value={
            "authenticated": False,
            "has_previous_auth": True,
            "spotify_user_id": None,
            "display_name": "Abc",
        }):
            response = client.get("/api/v1/auth/status")
        data = response.json()
        assert data["authenticated"] is False
        assert data["has_previous_auth"] is True

    def test_status_endpoint_passes_through_authenticated_state(self, client):
        """AC4: with a session, the endpoint surfaces an authenticated state + user id."""
        from services import spotify as svc
        self._login(client)
        with patch.object(svc, "get_auth_status", return_value={
            "authenticated": True,
            "has_previous_auth": True,
            "spotify_user_id": "user_abc",
            "display_name": "Abc",
        }):
            response = client.get("/api/v1/auth/status")
        data = response.json()
        assert data["authenticated"] is True
        assert data["has_previous_auth"] is True
        assert data["spotify_user_id"] == "user_abc"

    def test_status_response_does_not_leak_token_data(self, client):
        """NFR5: response must not contain access_token, refresh_token, spotify_token_json."""
        from services import spotify as svc
        self._login(client)
        with patch.object(svc, "get_auth_status", return_value={
            "authenticated": True,
            "has_previous_auth": True,
            "spotify_user_id": "user_abc",
            "display_name": "Abc",
        }):
            response = client.get("/api/v1/auth/status")
        data = response.json()
        assert "access_token" not in data
        assert "refresh_token" not in data
        assert "spotify_token_json" not in data
