"""Tests for Story 10.2: Per-User Login & Logout.

Exercises the real session round-trip (connect → callback → status/logout) through the
public auth_router WITHOUT overriding get_current_user, so the auth gate is genuinely
hit. Spotify is mocked at the service boundary (services.spotify.SpotifyOAuth / Spotify);
MemoryCacheHandler stays real. TestClient persists cookies across calls, so the
state/pending-creds round-trip works within one client.
"""
import json

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from models.user import User

FRONTEND_URL = "http://localhost:5173"


@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(engine, session):
    """Real session round-trip client. Points the get_session dependency and every
    module-level engine (used by complete_login + the cache handler) at one in-memory DB.
    """
    app.dependency_overrides[get_session] = lambda: session
    with patch("services.spotify.engine", engine), patch(
        "services.token_manager.engine", engine
    ):
        client = TestClient(app)
        yield client
    app.dependency_overrides.clear()


# --- helpers ---


def _connect(client, client_id="cid", client_secret="csec"):
    """POST /auth/connect and return the CSRF state the service generated."""
    with patch("services.spotify.SpotifyOAuth") as MockOAuth:
        MockOAuth.return_value.get_authorize_url.return_value = (
            "https://accounts.spotify.com/authorize?state=mocked"
        )
        r = client.post(
            "/api/v1/auth/connect",
            json={"client_id": client_id, "client_secret": client_secret},
        )
        assert r.status_code == 200, r.text
        state = MockOAuth.call_args.kwargs["state"]
        return r, state


def _login(
    client,
    spotify_user_id="spotify_abc",
    display_name="Alice",
    client_id="cid",
    client_secret="csec",
    token=None,
):
    """Run the full connect→callback round-trip; returns the callback response."""
    token = token or {"access_token": "tok", "refresh_token": "r", "expires_at": 9999999999}
    _, state = _connect(client, client_id, client_secret)
    with patch("services.spotify.SpotifyOAuth") as MockOAuth, patch(
        "services.spotify.Spotify"
    ) as MockSpotify:
        MockOAuth.return_value.get_access_token.return_value = token
        MockSpotify.return_value.me.return_value = {
            "id": spotify_user_id,
            "display_name": display_name,
        }
        return client.get(
            "/api/v1/auth/callback",
            params={"code": "code123", "state": state},
            follow_redirects=False,
        )


# --- AC#1: connect is public, CSRF-protected, returns auth_url ---


def test_connect_is_public_and_returns_auth_url(client):
    r, state = _connect(client)
    assert r.json()["auth_url"].startswith("https://accounts.spotify.com")
    assert state  # a random state was generated and passed to SpotifyOAuth


def test_connect_builds_oauth_from_given_credentials(client):
    with patch("services.spotify.SpotifyOAuth") as MockOAuth:
        MockOAuth.return_value.get_authorize_url.return_value = "https://x"
        client.post(
            "/api/v1/auth/connect",
            json={"client_id": "my_id", "client_secret": "my_secret"},
        )
    kwargs = MockOAuth.call_args.kwargs
    assert kwargs["client_id"] == "my_id"
    assert kwargs["client_secret"] == "my_secret"
    assert kwargs["state"]


# --- AC#2: callback validates state, resolves-or-creates user, opens session ---


def test_callback_state_mismatch_redirects_with_error_and_creates_no_user(client, session):
    _, _state = _connect(client)
    r = client.get(
        "/api/v1/auth/callback",
        params={"code": "abc", "state": "WRONG_STATE"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 307)
    assert "auth_error=1" in r.headers["location"]
    assert session.exec(select(User)).first() is None


def test_callback_missing_code_redirects_with_error(client):
    _, _state = _connect(client)
    r = client.get("/api/v1/auth/callback", params={"error": "access_denied"}, follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "auth_error=1" in r.headers["location"]


def test_callback_happy_path_creates_user_and_opens_session(client, session):
    r = _login(client, spotify_user_id="spotify_abc", display_name="Alice")
    assert r.status_code in (302, 307)
    assert r.headers["location"] == FRONTEND_URL
    assert "auth_error" not in r.headers["location"]

    user = session.exec(select(User).where(User.spotify_user_id == "spotify_abc")).one()
    assert user.display_name == "Alice"
    assert user.client_id == "cid"
    assert user.client_secret == "csec"
    assert json.loads(user.token_json)["access_token"] == "tok"
    assert user.created_at  # stamped on create


def test_callback_returning_user_reuses_row_no_duplicate(client, session):
    _login(client, spotify_user_id="same_user", display_name="First")
    client.post("/api/v1/auth/logout")
    # Same Spotify identity logs in again with refreshed creds/token
    _login(
        client,
        spotify_user_id="same_user",
        display_name="Renamed",
        client_id="cid2",
        client_secret="csec2",
        token={"access_token": "tok2", "expires_at": 9999999999},
    )

    users = session.exec(select(User).where(User.spotify_user_id == "same_user")).all()
    assert len(users) == 1
    assert users[0].display_name == "Renamed"
    assert users[0].client_id == "cid2"
    assert json.loads(users[0].token_json)["access_token"] == "tok2"


# --- AC#3: logout clears the session, keeps DB rows ---


def test_logout_clears_session_and_gate_then_rejects(client, session):
    _login(client)
    # Gate passes while logged in (blacklist GET reads DB only, no Spotify needed)
    assert client.get("/api/v1/blacklist").status_code != 401

    r = client.post("/api/v1/auth/logout")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    # Session cleared → gated route now 401
    assert client.get("/api/v1/blacklist").status_code == 401
    # DB row preserved for next login
    assert session.exec(select(User)).first() is not None


# --- AC#6: session-based auth status ---


def test_status_no_session_returns_unauthenticated(client):
    r = client.get("/api/v1/auth/status")
    assert r.status_code == 200
    body = r.json()
    assert body["authenticated"] is False
    assert body["has_previous_auth"] is False
    assert body["spotify_user_id"] is None
    assert body["display_name"] is None


def test_status_with_valid_session_reports_user(client):
    _login(client, spotify_user_id="spotify_xyz", display_name="Bob")
    token = {"access_token": "tok", "expires_at": 9999999999}
    with patch("services.spotify.SpotifyOAuth") as MockOAuth, patch(
        "services.spotify.Spotify"
    ) as MockSpotify:
        MockOAuth.return_value.get_cached_token.return_value = token
        MockOAuth.return_value.validate_token.return_value = token
        MockSpotify.return_value.me.return_value = {"id": "spotify_xyz", "display_name": "Bob"}
        r = client.get("/api/v1/auth/status")
    body = r.json()
    assert body["authenticated"] is True
    assert body["spotify_user_id"] == "spotify_xyz"
    assert body["display_name"] == "Bob"


# --- AC#4: per-user token cache isolation ---


def test_cache_handler_is_per_user(engine, session):
    from services.token_manager import SQLiteCacheHandler

    ua = User(spotify_user_id="user_a")
    ub = User(spotify_user_id="user_b")
    session.add(ua)
    session.add(ub)
    session.commit()
    session.refresh(ua)
    session.refresh(ub)

    with patch("services.token_manager.engine", engine):
        handler_a = SQLiteCacheHandler(ua.id)
        handler_b = SQLiteCacheHandler(ub.id)

        assert handler_a.get_cached_token() is None
        handler_a.save_token_to_cache({"access_token": "AAA"})

        assert handler_a.get_cached_token() == {"access_token": "AAA"}
        # User B is unaffected — tokens are isolated per user
        assert handler_b.get_cached_token() is None


def test_cache_handler_save_is_noop_when_user_missing(engine):
    from services.token_manager import SQLiteCacheHandler

    with patch("services.token_manager.engine", engine):
        handler = SQLiteCacheHandler(99999)
        handler.save_token_to_cache({"access_token": "x"})  # must not raise / create a row
        assert handler.get_cached_token() is None


# --- AC#8: no token/secret leakage in responses ---


def test_no_secret_leakage_in_status_or_connect(client):
    r_connect, _state = _connect(client)
    _login(client, spotify_user_id="spotify_leak", display_name="Carol")
    token = {"access_token": "supersecrettoken", "expires_at": 9999999999}
    with patch("services.spotify.SpotifyOAuth") as MockOAuth, patch(
        "services.spotify.Spotify"
    ) as MockSpotify:
        MockOAuth.return_value.get_cached_token.return_value = token
        MockOAuth.return_value.validate_token.return_value = token
        MockSpotify.return_value.me.return_value = {"id": "spotify_leak", "display_name": "Carol"}
        r_status = client.get("/api/v1/auth/status")

    for body in (r_connect.text, r_status.text):
        for secret in ("client_secret", "csec", "token_json", "access_token", "supersecrettoken"):
            assert secret not in body
