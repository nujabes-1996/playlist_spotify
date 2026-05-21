import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from models.playlist import Playlist


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


MOCK_PLAYLISTS = [
    {
        "spotify_id": "abc",
        "name": "My Mix",
        "image_url": "https://i.scdn.co/image/abc.jpg",
        "track_count": 42,
    },
    {
        "spotify_id": "def",
        "name": "Chill Vibes",
        "image_url": None,
        "track_count": 7,
    },
]


def test_get_returns_is_hidden_false_with_image_and_count(client):
    with patch(
        "routers.playlists.spotify_service.get_user_playlists",
        return_value=MOCK_PLAYLISTS,
    ):
        r = client.get("/api/v1/playlists")
    assert r.status_code == 200
    data = {p["spotify_id"]: p for p in r.json()}
    assert data["abc"]["is_hidden"] is False
    assert data["abc"]["image_url"] == "https://i.scdn.co/image/abc.jpg"
    assert data["abc"]["track_count"] == 42
    assert data["def"]["image_url"] is None
    assert data["def"]["track_count"] == 7


def test_get_preserves_is_hidden_on_existing(client, session):
    session.add(Playlist(spotify_id="abc", name="Old", is_included=False, is_hidden=True))
    session.commit()
    with patch(
        "routers.playlists.spotify_service.get_user_playlists",
        return_value=MOCK_PLAYLISTS,
    ):
        r = client.get("/api/v1/playlists")
    assert r.status_code == 200
    found = next(p for p in r.json() if p["spotify_id"] == "abc")
    assert found["is_hidden"] is True
    assert found["name"] == "My Mix"  # name still refreshed


def test_patch_is_hidden_true_clears_is_included(client, session):
    session.add(Playlist(spotify_id="abc", name="My Mix", is_included=True, is_hidden=False))
    session.commit()
    r = client.patch("/api/v1/playlists/abc", json={"is_hidden": True})
    assert r.status_code == 200
    body = r.json()
    assert body["is_hidden"] is True
    assert body["is_included"] is False
    # Verify atomically persisted
    row = session.exec(select(Playlist).where(Playlist.spotify_id == "abc")).first()
    assert row.is_hidden is True
    assert row.is_included is False


def test_patch_is_hidden_false_does_not_flip_is_included(client, session):
    session.add(Playlist(spotify_id="abc", name="My Mix", is_included=False, is_hidden=True))
    session.commit()
    r = client.patch("/api/v1/playlists/abc", json={"is_hidden": False})
    assert r.status_code == 200
    body = r.json()
    assert body["is_hidden"] is False
    assert body["is_included"] is False


def test_patch_empty_body_is_noop(client, session):
    session.add(Playlist(spotify_id="abc", name="My Mix", is_included=True, is_hidden=False))
    session.commit()
    r = client.patch("/api/v1/playlists/abc", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["is_included"] is True
    assert body["is_hidden"] is False


def test_sync_engine_query_excludes_hidden(session):
    session.add(Playlist(spotify_id="visible", name="Visible", is_included=True, is_hidden=False))
    session.add(Playlist(spotify_id="hidden", name="Hidden", is_included=True, is_hidden=True))
    session.commit()
    rows = session.exec(
        select(Playlist).where(Playlist.is_included == True, Playlist.is_hidden == False)  # noqa: E712
    ).all()
    ids = [r.spotify_id for r in rows]
    assert ids == ["visible"]
