import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
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
    {"spotify_id": "abc", "name": "My Mix"},
    {"spotify_id": "def", "name": "Chill Vibes"},
]


def test_get_playlists_returns_upserted_list(client):
    with patch("routers.playlists.spotify_service.get_user_playlists", return_value=MOCK_PLAYLISTS):
        r = client.get("/api/v1/playlists")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    spotify_ids = {p["spotify_id"] for p in data}
    assert spotify_ids == {"abc", "def"}
    for p in data:
        assert p["is_included"] is False


def test_get_playlists_updates_name_on_existing(client, session):
    session.add(Playlist(spotify_id="abc", name="Old Name"))
    session.commit()
    with patch("routers.playlists.spotify_service.get_user_playlists", return_value=MOCK_PLAYLISTS):
        r = client.get("/api/v1/playlists")
    assert r.status_code == 200
    updated = next(p for p in r.json() if p["spotify_id"] == "abc")
    assert updated["name"] == "My Mix"


def test_get_playlists_removes_deleted_from_spotify(client, session):
    session.add(Playlist(spotify_id="gone", name="Old Playlist"))
    session.commit()
    with patch("routers.playlists.spotify_service.get_user_playlists", return_value=MOCK_PLAYLISTS):
        r = client.get("/api/v1/playlists")
    assert r.status_code == 200
    ids = [p["spotify_id"] for p in r.json()]
    assert "gone" not in ids


def test_get_playlists_preserves_is_included(client, session):
    session.add(Playlist(spotify_id="abc", name="My Mix", is_included=True))
    session.commit()
    with patch("routers.playlists.spotify_service.get_user_playlists", return_value=MOCK_PLAYLISTS):
        r = client.get("/api/v1/playlists")
    assert r.status_code == 200
    found = next(p for p in r.json() if p["spotify_id"] == "abc")
    assert found["is_included"] is True


def test_patch_sets_included_true(client, session):
    session.add(Playlist(spotify_id="abc", name="My Mix", is_included=False))
    session.commit()
    r = client.patch("/api/v1/playlists/abc", json={"is_included": True})
    assert r.status_code == 200
    assert r.json()["is_included"] is True
    assert r.json()["spotify_id"] == "abc"


def test_patch_sets_included_false(client, session):
    session.add(Playlist(spotify_id="abc", name="My Mix", is_included=True))
    session.commit()
    r = client.patch("/api/v1/playlists/abc", json={"is_included": False})
    assert r.status_code == 200
    assert r.json()["is_included"] is False


def test_patch_nonexistent_returns_404(client):
    r = client.patch("/api/v1/playlists/nonexistent", json={"is_included": True})
    assert r.status_code == 404
