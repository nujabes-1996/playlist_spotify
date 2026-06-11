"""Tests for Story 10.1: User Model, Session Middleware & Auth Gate."""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from dependencies import get_current_user
from models.user import User


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


@pytest.fixture(name="auth_client")
def auth_client_fixture(session: Session):
    """Client with both DB session and an authenticated user injected."""
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: User(
        id=1, spotify_user_id="test_user"
    )
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="anon_client")
def anon_client_fixture(session: Session):
    """Client WITHOUT a current user override → hits the auth gate (401)."""
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# --- AC#1 / AC#6: User model ---


def test_user_table_round_trips_all_fields(session: Session):
    user = User(
        spotify_user_id="spotify_abc",
        display_name="Alice",
        client_id="cid",
        client_secret="csecret",
        token_json='{"access_token": "x"}',
        playlist_size=30,
        cron_expr="0 */6 * * *",
        target_playlist_id="pl-123",
        created_at="2026-06-09T10:00:00Z",
    )
    session.add(user)
    session.commit()

    fetched = session.exec(select(User)).one()
    assert fetched.id is not None
    assert fetched.spotify_user_id == "spotify_abc"
    assert fetched.display_name == "Alice"
    assert fetched.client_id == "cid"
    assert fetched.client_secret == "csecret"
    assert fetched.token_json == '{"access_token": "x"}'
    assert fetched.playlist_size == 30
    assert fetched.cron_expr == "0 */6 * * *"
    assert fetched.target_playlist_id == "pl-123"
    assert fetched.created_at == "2026-06-09T10:00:00Z"


def test_user_playlist_size_defaults_to_50(session: Session):
    user = User(spotify_user_id="spotify_def")
    session.add(user)
    session.commit()
    assert session.exec(select(User)).one().playlist_size == 50


# --- AC#4: auth gate rejects unauthenticated requests ---


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/v1/config"),
        ("get", "/api/v1/playlists"),
        ("post", "/api/v1/sync/run"),
        ("get", "/api/v1/blacklist"),
        ("get", "/api/v1/recently-added"),
    ],
)
def test_protected_routes_return_401_when_unauthenticated(anon_client, method, path):
    r = getattr(anon_client, method)(path)
    assert r.status_code == 401
    assert r.json()["detail"] == "Not authenticated"


# --- AC#4: public routes stay accessible ---


def test_health_is_public(anon_client):
    r = anon_client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_auth_status_is_public(anon_client):
    from services import spotify as svc

    with patch.object(
        svc,
        "get_auth_status",
        return_value={
            "authenticated": False,
            "has_previous_auth": False,
            "spotify_user_id": None,
        },
    ):
        r = anon_client.get("/api/v1/auth/status")
    assert r.status_code != 401
    assert r.status_code == 200


# --- AC#5: authenticated requests pass through unchanged ---


def test_authenticated_request_passes_through(auth_client):
    with patch(
        "routers.playlists.spotify_service.get_playlist_tracks_page",
        return_value={"items": [], "next_offset": None, "total": 0},
    ):
        r = auth_client.get("/api/v1/playlists/abc/tracks")
    assert r.status_code == 200


# --- AC#3: get_current_user behaviour ---


def test_get_current_user_raises_401_when_no_user_id(session: Session):
    from fastapi import HTTPException

    request = _make_request(session_data={})
    with pytest.raises(HTTPException) as exc:
        get_current_user(request, session)
    assert exc.value.status_code == 401
    assert exc.value.detail == "Not authenticated"


def test_get_current_user_raises_401_when_user_row_missing(session: Session):
    from fastapi import HTTPException

    request = _make_request(session_data={"user_id": 999})
    with pytest.raises(HTTPException) as exc:
        get_current_user(request, session)
    assert exc.value.status_code == 401


def test_get_current_user_returns_user_when_session_valid(session: Session):
    user = User(spotify_user_id="resolved_user")
    session.add(user)
    session.commit()
    session.refresh(user)

    request = _make_request(session_data={"user_id": user.id})
    resolved = get_current_user(request, session)
    assert resolved.id == user.id
    assert resolved.spotify_user_id == "resolved_user"


class _FakeRequest:
    def __init__(self, session_data):
        self.session = session_data


def _make_request(session_data):
    return _FakeRequest(session_data)


# --- AC#6: no token/secret leakage in responses ---


def test_no_secret_leakage_in_auth_status(anon_client):
    from services import spotify as svc

    with patch.object(
        svc,
        "get_auth_status",
        return_value={
            "authenticated": False,
            "has_previous_auth": False,
            "spotify_user_id": None,
        },
    ):
        r = anon_client.get("/api/v1/auth/status")
    body = r.text
    for secret in ("client_secret", "token_json", "csecret"):
        assert secret not in body
