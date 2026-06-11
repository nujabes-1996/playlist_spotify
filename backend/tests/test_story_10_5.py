"""Tests for Story 10.5: Production Hardening — Redirect URI, Session Cookie & Returning User.

Covers:
- AC#1: the prod SESSION_SECRET guard raises when secure+missing/empty/dev-default and does
  NOT raise in dev posture or with a strong secret. The guard runs at module import time, so
  these tests mutate env in a monkeypatch.context() and importlib.reload(main), then reload
  main once more with the ambient (clean) env to restore main.app for the rest of the suite.
- AC#2: GET /auth/status exposes redirect_uri (unauthenticated + authenticated), reflecting
  the backend's services.spotify.REDIRECT_URI.
- AC#5: returning-user resolve-or-create reuses the row (no duplicate) and re-persists creds/token.
- AC#7: no client_id/client_secret/token_json/access_token leaks into the status response.

Spotify is mocked at the service boundary (services.spotify.SpotifyOAuth / Spotify) exactly as
in test_story_10_2.py; MemoryCacheHandler stays real. TestClient persists cookies across calls.
"""
import importlib
import json

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool

import main
from database import get_session
from models.user import User
from services import spotify as spotify_service

DEV_DEFAULT = "insecure-dev-secret-change-me"


# ===== AC#1: prod-posture SESSION_SECRET guard =====


@pytest.mark.parametrize("secret", [None, "", DEV_DEFAULT])
def test_guard_raises_in_prod_when_secret_insecure(monkeypatch, secret):
    """Secure posture + (missing | empty | dev-default) secret → refuse to boot."""
    try:
        with monkeypatch.context() as m:
            m.setenv("SESSION_COOKIE_SECURE", "true")
            if secret is None:
                m.delenv("SESSION_SECRET", raising=False)
            else:
                m.setenv("SESSION_SECRET", secret)
            with pytest.raises(RuntimeError, match="SESSION_SECRET"):
                importlib.reload(main)
    finally:
        importlib.reload(main)  # env restored on context exit → clean main.app


def test_guard_allows_prod_with_strong_secret(monkeypatch):
    """Secure posture + a strong secret → boots normally."""
    try:
        with monkeypatch.context() as m:
            m.setenv("SESSION_COOKIE_SECURE", "true")
            m.setenv("SESSION_SECRET", "a" * 64)
            importlib.reload(main)  # must not raise
    finally:
        importlib.reload(main)


def test_guard_allows_dev_posture_without_secret(monkeypatch):
    """Dev posture (SESSION_COOKIE_SECURE unset) + no secret → insecure default allowed."""
    try:
        with monkeypatch.context() as m:
            m.delenv("SESSION_COOKIE_SECURE", raising=False)
            m.delenv("SESSION_SECRET", raising=False)
            importlib.reload(main)  # must not raise — local HTTP dev must keep working
    finally:
        importlib.reload(main)


# ===== fixtures for the request-level tests (mirror test_story_10_2.py) =====


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
    main.app.dependency_overrides[get_session] = lambda: session
    with patch("services.spotify.engine", engine), patch(
        "services.token_manager.engine", engine
    ):
        client = TestClient(main.app)
        yield client
    main.app.dependency_overrides.clear()


def _connect(client, client_id="cid", client_secret="csec"):
    with patch("services.spotify.SpotifyOAuth") as MockOAuth:
        MockOAuth.return_value.get_authorize_url.return_value = (
            "https://accounts.spotify.com/authorize?state=mocked"
        )
        r = client.post(
            "/api/v1/auth/connect",
            json={"client_id": client_id, "client_secret": client_secret},
        )
        assert r.status_code == 200, r.text
        return r, MockOAuth.call_args.kwargs["state"]


def _login(
    client,
    spotify_user_id="spotify_abc",
    display_name="Alice",
    client_id="cid",
    client_secret="csec",
    token=None,
):
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


# ===== AC#2: redirect_uri exposed on /auth/status =====


def test_status_exposes_redirect_uri_unauthenticated(client):
    r = client.get("/api/v1/auth/status")
    assert r.status_code == 200
    body = r.json()
    assert body["redirect_uri"] == spotify_service.REDIRECT_URI


def test_status_exposes_redirect_uri_authenticated(client):
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
    assert body["redirect_uri"] == spotify_service.REDIRECT_URI


def test_status_redirect_uri_reflects_backend_value(client):
    """The field is read from the backend constant at request time (env source of truth)."""
    forced = "https://example.com/api/v1/auth/callback"
    with patch("services.spotify.REDIRECT_URI", forced):
        r = client.get("/api/v1/auth/status")
    assert r.json()["redirect_uri"] == forced


# ===== AC#5: returning-user resolve-or-create reuses the row =====


def test_returning_user_reuses_row_and_repersists(client, session):
    _login(client, spotify_user_id="same_user", display_name="First")
    client.post("/api/v1/auth/logout")
    _login(
        client,
        spotify_user_id="same_user",
        display_name="Renamed",
        client_id="cid2",
        client_secret="csec2",
        token={"access_token": "tok2", "expires_at": 9999999999},
    )

    users = session.exec(select(User).where(User.spotify_user_id == "same_user")).all()
    assert len(users) == 1  # no duplicate
    assert users[0].display_name == "Renamed"
    assert users[0].client_id == "cid2"
    assert users[0].client_secret == "csec2"
    assert json.loads(users[0].token_json)["access_token"] == "tok2"


# ===== AC#7: no secret/token leakage when redirect_uri is added =====


def test_status_does_not_leak_secrets(client):
    _login(client, spotify_user_id="spotify_leak", display_name="Carol")
    token = {"access_token": "supersecrettoken", "expires_at": 9999999999}
    with patch("services.spotify.SpotifyOAuth") as MockOAuth, patch(
        "services.spotify.Spotify"
    ) as MockSpotify:
        MockOAuth.return_value.get_cached_token.return_value = token
        MockOAuth.return_value.validate_token.return_value = token
        MockSpotify.return_value.me.return_value = {"id": "spotify_leak", "display_name": "Carol"}
        r = client.get("/api/v1/auth/status")
    body = r.text
    for secret in ("client_secret", "client_id", "token_json", "access_token", "supersecrettoken", "csec"):
        assert secret not in body
