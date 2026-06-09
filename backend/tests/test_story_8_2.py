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


# --- Router-level tests (service mocked) ---


def test_returns_empty_list_when_dynamic_playlist_id_missing(client):
    with patch(
        "routers.recently_added.spotify_service.get_recently_added_tracks",
        return_value=[],
    ):
        r = client.get("/api/v1/recently-added")
    assert r.status_code == 200
    assert r.json() == []


def test_returns_tracks_with_exact_shape(client):
    payload = [
        {
            "spotify_id": "track-1",
            "title": "Song",
            "artists": ["A", "B"],
            "album": "Album",
            "image_url": "https://i.scdn.co/image/abc.jpg",
            "added_at": "2026-05-20T10:00:00Z",
            "duration_ms": 240000,
            "explicit": True,
            "has_video": False,
            "is_blacklisted": False,
        }
    ]
    with patch(
        "routers.recently_added.spotify_service.get_recently_added_tracks",
        return_value=payload,
    ):
        r = client.get("/api/v1/recently-added")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    track = body[0]
    expected_keys = {
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
    assert set(track.keys()) == expected_keys
    assert track["spotify_id"] == "track-1"
    assert track["title"] == "Song"
    assert track["artists"] == ["A", "B"]
    assert track["album"] == "Album"
    assert track["image_url"] == "https://i.scdn.co/image/abc.jpg"
    assert track["added_at"] == "2026-05-20T10:00:00Z"
    assert track["duration_ms"] == 240000
    assert track["explicit"] is True
    assert track["has_video"] is False


def test_returns_401_when_not_authenticated(client):
    with patch(
        "routers.recently_added.spotify_service.get_recently_added_tracks",
        side_effect=ValueError("Not authenticated — run OAuth2 flow first"),
    ):
        r = client.get("/api/v1/recently-added")
    assert r.status_code == 401
    assert "Not authenticated" in r.json()["detail"]


def test_returns_502_on_spotify_exception(client):
    with patch(
        "routers.recently_added.spotify_service.get_recently_added_tracks",
        side_effect=SpotifyException(http_status=500, code=-1, msg="boom"),
    ):
        r = client.get("/api/v1/recently-added")
    assert r.status_code == 502
    assert "boom" in r.json()["detail"]


def test_returns_empty_list_when_playlist_deleted_on_spotify(client):
    with patch(
        "routers.recently_added.spotify_service.get_recently_added_tracks",
        return_value=[],
    ):
        r = client.get("/api/v1/recently-added")
    assert r.status_code == 200
    assert r.json() == []


# --- Service-level unit tests ---


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


def _seed_config(engine, dynamic_playlist_id="dyn-1"):
    with Session(engine) as s:
        s.add(Config(client_id="cid", client_secret="csec", dynamic_playlist_id=dynamic_playlist_id))
        s.commit()


def test_service_paginates_and_concatenates(engine):
    from services import spotify as svc

    _seed_config(engine)
    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {"id": "dyn-1"}
    page1 = {
        "items": [_make_track(f"t{i}") for i in range(100)],
        "next": "next-url",
    }
    page2 = {
        "items": [_make_track(f"t{i}") for i in range(100, 150)],
        "next": None,
    }
    mock_sp.playlist_items.side_effect = [page1, page2]

    with patch.object(svc, "engine", engine), patch.object(
        svc, "get_authenticated_client", return_value=mock_sp
    ):
        result = svc.get_recently_added_tracks()

    assert len(result) == 150
    assert [t["spotify_id"] for t in result] == [f"t{i}" for i in range(150)]


def test_service_skips_null_and_local_tracks(engine):
    from services import spotify as svc

    _seed_config(engine)
    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {"id": "dyn-1"}
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

    with patch.object(svc, "engine", engine), patch.object(
        svc, "get_authenticated_client", return_value=mock_sp
    ):
        result = svc.get_recently_added_tracks()

    assert len(result) == 1
    assert result[0]["spotify_id"] == "valid-1"


def test_service_sets_image_url_null_when_no_album_images(engine):
    from services import spotify as svc

    _seed_config(engine)
    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {"id": "dyn-1"}
    mock_sp.playlist_items.return_value = {
        "items": [_make_track("t1", album={"name": "Alb", "images": []})],
        "next": None,
    }

    with patch.object(svc, "engine", engine), patch.object(
        svc, "get_authenticated_client", return_value=mock_sp
    ):
        result = svc.get_recently_added_tracks()

    assert len(result) == 1
    assert result[0]["image_url"] is None


def test_service_flattens_artists_to_names(engine):
    from services import spotify as svc

    _seed_config(engine)
    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {"id": "dyn-1"}
    mock_sp.playlist_items.return_value = {
        "items": [
            _make_track("t1", artists=[{"name": "A"}, {"name": "B"}]),
        ],
        "next": None,
    }

    with patch.object(svc, "engine", engine), patch.object(
        svc, "get_authenticated_client", return_value=mock_sp
    ):
        result = svc.get_recently_added_tracks()

    assert result[0]["artists"] == ["A", "B"]


def test_service_returns_empty_when_playlist_gone(engine):
    from services import spotify as svc

    _seed_config(engine, dynamic_playlist_id="ghost")
    mock_sp = MagicMock()
    mock_sp.playlist.side_effect = SpotifyException(
        http_status=404, code=-1, msg="not found"
    )

    with patch.object(svc, "engine", engine), patch.object(
        svc, "get_authenticated_client", return_value=mock_sp
    ):
        result = svc.get_recently_added_tracks()

    assert result == []
    # Verify config.dynamic_playlist_id NOT mutated
    with Session(engine) as s:
        from sqlmodel import select

        cfg = s.exec(select(Config)).first()
        assert cfg.dynamic_playlist_id == "ghost"


def test_service_returns_empty_when_no_config(engine):
    from services import spotify as svc

    # No Config row seeded
    with patch.object(svc, "engine", engine), patch.object(
        svc, "get_authenticated_client"
    ) as auth_mock:
        result = svc.get_recently_added_tracks()

    assert result == []
    auth_mock.assert_not_called()


def test_service_reraises_non_404_spotify_exception(engine):
    from services import spotify as svc

    _seed_config(engine)
    mock_sp = MagicMock()
    mock_sp.playlist.side_effect = SpotifyException(
        http_status=500, code=-1, msg="boom"
    )

    with patch.object(svc, "engine", engine), patch.object(
        svc, "get_authenticated_client", return_value=mock_sp
    ):
        with pytest.raises(SpotifyException):
            svc.get_recently_added_tracks()
