import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app
from database import get_session


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


def _make_item(track_id, **overrides):
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


# --- Router-level tests ---


def test_nominal_pagination_regular_playlist(client):
    payload = {
        "items": [
            {
                "spotify_id": f"t{i}",
                "title": f"T{i}",
                "artists": ["A"],
                "album": "Alb",
                "image_url": None,
                "added_at": "2026-05-20T10:00:00Z",
                "duration_ms": 1,
                "explicit": False,
                "has_video": False,
                "is_blacklisted": False,
            }
            for i in range(50)
        ],
        "next_offset": 50,
        "total": 200,
    }
    with patch(
        "routers.playlists.spotify_service.get_playlist_tracks_page",
        return_value=payload,
    ):
        r = client.get("/api/v1/playlists/abc/tracks?limit=50&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)
    assert len(body["items"]) == 50
    assert body["next_offset"] == 50
    assert body["total"] == 200
    assert set(body["items"][0].keys()) == EXPECTED_KEYS


def test_last_page_next_offset_is_null(client):
    payload = {
        "items": [
            {
                "spotify_id": f"t{i}",
                "title": f"T{i}",
                "artists": ["A"],
                "album": "Alb",
                "image_url": None,
                "added_at": "x",
                "duration_ms": 1,
                "explicit": False,
                "has_video": False,
                "is_blacklisted": False,
            }
            for i in range(35)
        ],
        "next_offset": None,
        "total": 185,
    }
    with patch(
        "routers.playlists.spotify_service.get_playlist_tracks_page",
        return_value=payload,
    ):
        r = client.get("/api/v1/playlists/abc/tracks?limit=50&offset=150")
    assert r.status_code == 200
    body = r.json()
    assert body["next_offset"] is None
    assert len(body["items"]) == 35
    assert body["total"] == 185
    # Verify JSON literally serializes null
    assert '"next_offset":null' in r.text.replace(" ", "")


def test_offset_beyond_total_returns_empty_page(client):
    payload = {"items": [], "next_offset": None, "total": 200}
    with patch(
        "routers.playlists.spotify_service.get_playlist_tracks_page",
        return_value=payload,
    ):
        r = client.get("/api/v1/playlists/abc/tracks?offset=10000")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["next_offset"] is None
    assert body["total"] == 200


def test_limit_over_100_returns_422(client):
    r = client.get("/api/v1/playlists/abc/tracks?limit=200")
    assert r.status_code == 422


def test_limit_zero_returns_422(client):
    r = client.get("/api/v1/playlists/abc/tracks?limit=0")
    assert r.status_code == 422


def test_negative_offset_returns_422(client):
    r = client.get("/api/v1/playlists/abc/tracks?offset=-1")
    assert r.status_code == 422


def test_liked_songs_branch_uses_saved_tracks(client):
    from services import spotify as svc

    mock_sp = MagicMock()
    mock_sp.current_user_saved_tracks.return_value = {
        "items": [_make_item(f"t{i}") for i in range(50)],
        "total": 535,
    }

    with patch.object(svc, "get_authenticated_client", return_value=mock_sp):
        r = client.get("/api/v1/playlists/liked_songs/tracks?limit=50&offset=0")

    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 50
    assert body["next_offset"] == 50
    assert body["total"] == 535
    mock_sp.current_user_saved_tracks.assert_called_once_with(limit=50, offset=0)
    mock_sp.playlist_items.assert_not_called()


# --- Service-level tests ---


def test_service_skipped_items_advance_offset_by_raw_page_len():
    from services import spotify as svc

    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {"tracks": {"total": 100}}
    raw_items = [
        None,
        _make_item("t-local", is_local=True),
        _make_item("valid-1"),
        {"added_at": "x", "is_local": True, "track": None},
        _make_item("valid-2"),
    ]
    mock_sp.playlist_items.return_value = {
        "items": raw_items,
        "total": 100,
    }

    with patch.object(svc, "get_authenticated_client", return_value=mock_sp):
        result = svc.get_playlist_tracks_page("pl-1", limit=5, offset=0)

    # Kept items: only "valid-1" and "valid-2" (3rd item t-local has is_local=True
    # at the item AND track level — second case path: skip via outer is_local).
    # Wait — the function only skips item.get("is_local") at outer level and
    # track.get("is_local") at inner level. _make_item sets is_local=False at item
    # level but we pass is_local=True to the track. So t-local is skipped.
    assert len(result["items"]) == 2
    # next_offset advances by RAW page length (5), not kept length (2)
    assert result["next_offset"] == 5
    assert result["total"] == 100


def test_service_liked_songs_next_offset_null_at_end():
    from services import spotify as svc

    mock_sp = MagicMock()
    mock_sp.current_user_saved_tracks.return_value = {
        "items": [_make_item(f"t{i}") for i in range(35)],
        "total": 185,
    }

    with patch.object(svc, "get_authenticated_client", return_value=mock_sp):
        result = svc.get_playlist_tracks_page("liked_songs", limit=50, offset=150)

    assert len(result["items"]) == 35
    # offset 150 + raw 35 = 185 = total → next_offset is None
    assert result["next_offset"] is None
    assert result["total"] == 185
