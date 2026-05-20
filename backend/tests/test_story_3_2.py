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


SPOTIFY_PLAYLISTS = [
    {"spotify_id": "abc", "name": "My Mix"},
    {"spotify_id": "def", "name": "Chill Vibes"},
]


def test_is_included_preserved_on_repeated_get(client, session):
    """AC1 — Upsert must never reset is_included for existing playlists."""
    session.add(Playlist(spotify_id="abc", name="My Mix", is_included=True))
    session.add(Playlist(spotify_id="def", name="Chill Vibes", is_included=False))
    session.commit()

    with patch("routers.playlists.spotify_service.get_user_playlists", return_value=SPOTIFY_PLAYLISTS):
        r = client.get("/api/v1/playlists")

    assert r.status_code == 200
    data = {p["spotify_id"]: p for p in r.json()}
    assert data["abc"]["is_included"] is True
    assert data["def"]["is_included"] is False


def test_new_playlist_appears_with_false_default(client, session):
    """AC2 — New Spotify playlist (not yet in DB) appears with is_included=False."""
    session.add(Playlist(spotify_id="abc", name="My Mix", is_included=True))
    session.commit()

    spotify_with_new = SPOTIFY_PLAYLISTS + [{"spotify_id": "xyz", "name": "New Finds"}]
    with patch("routers.playlists.spotify_service.get_user_playlists", return_value=spotify_with_new):
        r = client.get("/api/v1/playlists")

    assert r.status_code == 200
    data = {p["spotify_id"]: p for p in r.json()}
    assert "xyz" in data
    assert data["xyz"]["is_included"] is False
    assert data["abc"]["is_included"] is True


def test_removed_playlist_not_in_list(client, session):
    """AC3 — Playlist deleted from Spotify (is_included=False) is removed from the response."""
    session.add(Playlist(spotify_id="gone", name="Removed", is_included=False))
    session.add(Playlist(spotify_id="abc", name="My Mix", is_included=False))
    session.commit()

    with patch("routers.playlists.spotify_service.get_user_playlists", return_value=[SPOTIFY_PLAYLISTS[0]]):
        r = client.get("/api/v1/playlists")

    assert r.status_code == 200
    ids = [p["spotify_id"] for p in r.json()]
    assert "gone" not in ids
    assert "abc" in ids


def test_included_playlist_removed_when_deleted_from_spotify(client, session):
    """AC4 — Previously included playlist (is_included=True) deleted from Spotify is removed from DB."""
    session.add(Playlist(spotify_id="was_included", name="Fave Mix", is_included=True))
    session.add(Playlist(spotify_id="abc", name="My Mix", is_included=False))
    session.commit()

    with patch("routers.playlists.spotify_service.get_user_playlists", return_value=[SPOTIFY_PLAYLISTS[0]]):
        r = client.get("/api/v1/playlists")

    assert r.status_code == 200
    ids = [p["spotify_id"] for p in r.json()]
    assert "was_included" not in ids
    assert "abc" in ids
