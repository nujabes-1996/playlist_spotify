import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool
from spotipy import SpotifyException

from main import app
from database import get_session
from models.config import Config


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
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


EXPECTED_KEYS = {
    "spotify_id",
    "title",
    "artists",
    "album",
    "image_url",
    "added_at",
    "duration_ms",
    "explicit",
    "has_video",
    "is_blacklisted",
}


def _make_track(track_id, **overrides):
    track = {
        "id": track_id,
        "name": f"Track {track_id}",
        "duration_ms": 200000,
        "explicit": False,
        "is_local": False,
        "is_video": False,
        "artists": [{"name": "Artist"}],
        "album": {"name": "Album", "images": [{"url": f"https://img/{track_id}.jpg"}]},
    }
    track.update(overrides)
    return {"added_at": "2026-05-20T10:00:00Z", "is_local": False, "track": track}


# --- Router-level tests (service mocked) ---


def test_returns_200_and_array_for_regular_playlist(client):
    payload = {
        "items": [
            {
                "spotify_id": "t1",
                "title": "Song",
                "artists": ["A"],
                "album": "Album",
                "image_url": "https://i.scdn.co/x.jpg",
                "added_at": "2026-05-20T10:00:00Z",
                "duration_ms": 200000,
                "explicit": False,
                "has_video": False,
                "is_blacklisted": False,
            }
        ],
        "next_offset": None,
        "total": 1,
    }
    with patch(
        "routers.playlists.spotify_service.get_playlist_tracks_page",
        return_value=payload,
    ):
        r = client.get("/api/v1/playlists/abc123/tracks")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    assert len(body["items"]) == 1
    assert set(body["items"][0].keys()) == EXPECTED_KEYS
    assert body["items"][0]["spotify_id"] == "t1"
    assert body["next_offset"] is None
    assert body["total"] == 1


def test_returns_404_when_playlist_not_found(client):
    with patch(
        "routers.playlists.spotify_service.get_playlist_tracks_page",
        side_effect=SpotifyException(http_status=404, code=-1, msg="not found"),
    ):
        r = client.get("/api/v1/playlists/nonexistent/tracks")
    assert r.status_code == 404
    assert r.json()["detail"] == "Playlist not found"


def test_returns_401_when_not_authenticated(client):
    with patch(
        "routers.playlists.spotify_service.get_playlist_tracks_page",
        side_effect=ValueError("Not authenticated — run OAuth2 flow first"),
    ):
        r = client.get("/api/v1/playlists/abc/tracks")
    assert r.status_code == 401
    assert "Not authenticated" in r.json()["detail"]


def test_returns_502_on_non_404_spotify_error(client):
    with patch(
        "routers.playlists.spotify_service.get_playlist_tracks_page",
        side_effect=SpotifyException(http_status=500, code=-1, msg="boom"),
    ):
        r = client.get("/api/v1/playlists/abc/tracks")
    assert r.status_code == 502
    assert "boom" in r.json()["detail"]


def test_liked_songs_sentinel_routes_to_service(client):
    with patch(
        "routers.playlists.spotify_service.get_playlist_tracks_page",
        return_value={"items": [], "next_offset": None, "total": 0},
    ) as svc_mock:
        r = client.get("/api/v1/playlists/liked_songs/tracks")
    assert r.status_code == 200
    svc_mock.assert_called_once_with("liked_songs", 50, 0)


# --- Service-level unit tests ---


def test_service_paginates_and_concatenates_for_regular_playlist():
    from services import spotify as svc

    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {"id": "pl-1"}
    page1 = {
        "items": [_make_track(f"t{i}") for i in range(100)],
        "next": "next-url",
    }
    page2 = {
        "items": [_make_track(f"t{i}") for i in range(100, 150)],
        "next": None,
    }
    mock_sp.playlist_items.side_effect = [page1, page2]

    with patch.object(svc, "get_authenticated_client", return_value=mock_sp):
        result = svc.get_playlist_tracks_full("pl-1")

    assert len(result) == 150
    assert [t["spotify_id"] for t in result] == [f"t{i}" for i in range(150)]
    assert set(result[0].keys()) == EXPECTED_KEYS


def test_service_skips_null_and_local_tracks():
    from services import spotify as svc

    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {"id": "pl-1"}
    mock_sp.playlist_items.return_value = {
        "items": [
            None,
            {"added_at": "x", "is_local": True, "track": None},
            _make_track("t-local", is_local=True),
            {"added_at": "x", "is_local": False, "track": {"id": None}},
            _make_track("valid-1"),
        ],
        "next": None,
    }

    with patch.object(svc, "get_authenticated_client", return_value=mock_sp):
        result = svc.get_playlist_tracks_full("pl-1")

    assert len(result) == 1
    assert result[0]["spotify_id"] == "valid-1"


def test_service_sets_image_url_null_when_no_album_images():
    from services import spotify as svc

    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {"id": "pl-1"}
    mock_sp.playlist_items.return_value = {
        "items": [_make_track("t1", album={"name": "Alb", "images": []})],
        "next": None,
    }

    with patch.object(svc, "get_authenticated_client", return_value=mock_sp):
        result = svc.get_playlist_tracks_full("pl-1")

    assert len(result) == 1
    assert result[0]["image_url"] is None


def test_service_flattens_artists_to_names():
    from services import spotify as svc

    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {"id": "pl-1"}
    mock_sp.playlist_items.return_value = {
        "items": [
            _make_track("t1", artists=[{"name": "A"}, {"name": "B"}]),
        ],
        "next": None,
    }

    with patch.object(svc, "get_authenticated_client", return_value=mock_sp):
        result = svc.get_playlist_tracks_full("pl-1")

    assert result[0]["artists"] == ["A", "B"]


def test_service_liked_songs_uses_saved_tracks_api():
    from services import spotify as svc

    mock_sp = MagicMock()
    mock_sp.current_user_saved_tracks.return_value = {
        "items": [
            {
                "added_at": "2026-05-20T10:00:00Z",
                "track": {
                    "id": "t1",
                    "name": "Liked",
                    "duration_ms": 180000,
                    "explicit": False,
                    "is_local": False,
                    "is_video": False,
                    "artists": [{"name": "A"}],
                    "album": {"name": "Alb", "images": [{"url": "https://img/t1.jpg"}]},
                },
            },
        ],
        "next": None,
    }

    with patch.object(svc, "get_authenticated_client", return_value=mock_sp):
        result = svc.get_playlist_tracks_full("liked_songs")

    assert len(result) == 1
    assert result[0]["spotify_id"] == "t1"
    assert result[0]["title"] == "Liked"
    assert set(result[0].keys()) == EXPECTED_KEYS
    mock_sp.playlist_items.assert_not_called()
    mock_sp.playlist.assert_not_called()


def test_service_raises_spotify_exception_on_404_probe():
    from services import spotify as svc

    mock_sp = MagicMock()
    mock_sp.playlist.side_effect = SpotifyException(
        http_status=404, code=-1, msg="not found"
    )

    with patch.object(svc, "get_authenticated_client", return_value=mock_sp):
        with pytest.raises(SpotifyException) as exc_info:
            svc.get_playlist_tracks_full("ghost")
    assert exc_info.value.http_status == 404
    mock_sp.playlist_items.assert_not_called()


def test_service_reraises_non_404_spotify_exception():
    from services import spotify as svc

    mock_sp = MagicMock()
    mock_sp.playlist.side_effect = SpotifyException(
        http_status=500, code=-1, msg="boom"
    )

    with patch.object(svc, "get_authenticated_client", return_value=mock_sp):
        with pytest.raises(SpotifyException) as exc_info:
            svc.get_playlist_tracks_full("pl-1")
    assert exc_info.value.http_status == 500
