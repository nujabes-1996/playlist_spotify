"""Story 9.7 — is_blacklisted flag on track responses.

Covers AC #5: get_recently_added_tracks and get_playlist_tracks_full both
set is_blacklisted correctly per track, including the Liked Songs branch
and the empty-blacklist case. Plus an API-contract test ensuring the JSON
response shape carries the new field.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from models.config import Config
from models.track_blacklist import TrackBlacklist


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


def _seed_blacklist(engine, *spotify_ids):
    with Session(engine) as s:
        for sid in spotify_ids:
            s.add(TrackBlacklist(spotify_id=sid, blacklisted_at="2026-05-20T00:00:00Z"))
        s.commit()


# ────────────────────────────────────────────────────────────
# (a) get_recently_added_tracks reflects blacklist membership
# ────────────────────────────────────────────────────────────

def test_recently_added_sets_is_blacklisted_per_track(engine):
    from services import spotify as svc

    _seed_config(engine)
    _seed_blacklist(engine, "t1")

    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {"id": "dyn-1"}
    mock_sp.playlist_items.return_value = {
        "items": [_make_track("t1"), _make_track("t2"), _make_track("t3")],
        "next": None,
    }

    with patch.object(svc, "engine", engine), patch.object(
        svc, "get_authenticated_client", return_value=mock_sp
    ):
        result = svc.get_recently_added_tracks()

    flags = {t["spotify_id"]: t["is_blacklisted"] for t in result}
    assert flags == {"t1": True, "t2": False, "t3": False}


# ────────────────────────────────────────────────────────────
# (b) get_playlist_tracks_full — regular playlist
# ────────────────────────────────────────────────────────────

def test_playlist_tracks_full_sets_is_blacklisted_per_track(engine):
    from services import spotify as svc

    _seed_blacklist(engine, "t2")

    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {"id": "pl-1"}
    mock_sp.playlist_items.return_value = {
        "items": [_make_track("t1"), _make_track("t2"), _make_track("t3")],
        "next": None,
    }

    with patch.object(svc, "engine", engine), patch.object(
        svc, "get_authenticated_client", return_value=mock_sp
    ):
        result = svc.get_playlist_tracks_full("pl-1")

    flags = {t["spotify_id"]: t["is_blacklisted"] for t in result}
    assert flags == {"t1": False, "t2": True, "t3": False}


# ────────────────────────────────────────────────────────────
# (c) get_playlist_tracks_full — Liked Songs branch
# ────────────────────────────────────────────────────────────

def test_playlist_tracks_full_liked_songs_sets_is_blacklisted(engine):
    from services import spotify as svc

    _seed_blacklist(engine, "lk2")

    mock_sp = MagicMock()
    mock_sp.current_user_saved_tracks.return_value = {
        "items": [
            {
                "added_at": "2026-05-20T10:00:00Z",
                "track": {
                    "id": "lk1",
                    "name": "Liked 1",
                    "duration_ms": 180000,
                    "explicit": False,
                    "is_local": False,
                    "is_video": False,
                    "artists": [{"name": "A"}],
                    "album": {"name": "Alb", "images": [{"url": "https://img/lk1.jpg"}]},
                },
            },
            {
                "added_at": "2026-05-20T10:00:00Z",
                "track": {
                    "id": "lk2",
                    "name": "Liked 2",
                    "duration_ms": 180000,
                    "explicit": False,
                    "is_local": False,
                    "is_video": False,
                    "artists": [{"name": "B"}],
                    "album": {"name": "Alb", "images": []},
                },
            },
        ],
        "next": None,
    }

    with patch.object(svc, "engine", engine), patch.object(
        svc, "get_authenticated_client", return_value=mock_sp
    ):
        result = svc.get_playlist_tracks_full("liked_songs")

    flags = {t["spotify_id"]: t["is_blacklisted"] for t in result}
    assert flags == {"lk1": False, "lk2": True}


# ────────────────────────────────────────────────────────────
# (d) Empty blacklist → every track is_blacklisted=False
# ────────────────────────────────────────────────────────────

def test_empty_blacklist_means_every_track_false(engine):
    from services import spotify as svc

    _seed_config(engine)

    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {"id": "dyn-1"}
    mock_sp.playlist_items.return_value = {
        "items": [_make_track("t1"), _make_track("t2")],
        "next": None,
    }

    with patch.object(svc, "engine", engine), patch.object(
        svc, "get_authenticated_client", return_value=mock_sp
    ):
        result = svc.get_recently_added_tracks()

    assert all(t["is_blacklisted"] is False for t in result)


# ────────────────────────────────────────────────────────────
# (e) API contract — both endpoints expose is_blacklisted in JSON
# ────────────────────────────────────────────────────────────

def test_recently_added_endpoint_exposes_is_blacklisted(client):
    payload = [
        {
            "spotify_id": "t1",
            "title": "Song",
            "artists": ["A"],
            "album": "Album",
            "image_url": None,
            "added_at": "2026-05-20T10:00:00Z",
            "duration_ms": 200000,
            "explicit": False,
            "has_video": False,
            "is_blacklisted": True,
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
    assert body[0]["is_blacklisted"] is True


def test_playlist_tracks_endpoint_exposes_is_blacklisted(client):
    payload = {
        "items": [
            {
                "spotify_id": "t1",
                "title": "Song",
                "artists": ["A"],
                "album": "Album",
                "image_url": None,
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
        r = client.get("/api/v1/playlists/abc/tracks")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["is_blacklisted"] is False
