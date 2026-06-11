import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool

from models.playlist import Playlist
from models.sync_log import SyncLog
from models.track_blacklist import TrackBlacklist
from models.user import User
import services.sync_engine as sync_engine
import services.blacklist_service as blacklist_service


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # Story 10.2: scheduled sync resolves the single logged-in user
        session.add(User(spotify_user_id="scheduled", client_id="c", client_secret="s", token_json="{}"))
        session.commit()
        yield session


PLAYLIST_TRACKS = [
    {"spotify_id": "t1", "uri": "spotify:track:t1", "added_at": "2026-05-10T00:00:00Z"},
    {"spotify_id": "t2", "uri": "spotify:track:t2", "added_at": "2026-05-08T00:00:00Z"},
]


# ────────────────────────────────────────────────────────────
# (a)(b) blacklist_service.get_blacklisted_ids
# ────────────────────────────────────────────────────────────

def test_get_blacklisted_ids_empty(session):
    assert blacklist_service.get_blacklisted_ids(session, 1) == set()


def test_get_blacklisted_ids_returns_all_ids(session):
    session.add(TrackBlacklist(user_id=1, spotify_id="id1", blacklisted_at="2026-05-20T00:00:00Z"))
    session.add(TrackBlacklist(user_id=1, spotify_id="id2", blacklisted_at="2026-05-20T00:00:00Z"))
    session.commit()

    assert blacklist_service.get_blacklisted_ids(session, 1) == {"id1", "id2"}


# ────────────────────────────────────────────────────────────
# (c) baseline — empty blacklist preserves prior behavior
# ────────────────────────────────────────────────────────────

def test_run_sync_unchanged_when_blacklist_empty(session):
    session.add(Playlist(user_id=1, spotify_id="pl1", name="Mix", is_included=True))
    _user = session.exec(select(User)).first()
    _user.playlist_size = 2
    session.add(_user)
    session.commit()

    mock_sp = MagicMock()
    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch("services.sync_engine.spotify_service.get_playlist_tracks", return_value=PLAYLIST_TRACKS),
        patch("services.sync_engine.spotify_service.get_or_create_dynamic_playlist", return_value="dyn_id"),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks") as mock_replace,
    ):
        sync_engine.run_sync(1)

    captured_uris = mock_replace.call_args[0][1]
    assert captured_uris == ["spotify:track:t1", "spotify:track:t2"]


# ────────────────────────────────────────────────────────────
# (d) one blacklisted track is excluded
# ────────────────────────────────────────────────────────────

def test_run_sync_excludes_blacklisted_track(session):
    session.add(Playlist(user_id=1, spotify_id="pl1", name="Mix", is_included=True))
    _user = session.exec(select(User)).first()
    _user.playlist_size = 2
    session.add(_user)
    session.add(TrackBlacklist(user_id=1, spotify_id="t1", blacklisted_at="2026-05-20T00:00:00Z"))
    session.commit()

    mock_sp = MagicMock()
    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch("services.sync_engine.spotify_service.get_playlist_tracks", return_value=PLAYLIST_TRACKS),
        patch("services.sync_engine.spotify_service.get_or_create_dynamic_playlist", return_value="dyn_id"),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks") as mock_replace,
    ):
        sync_engine.run_sync(1)

    captured_uris = mock_replace.call_args[0][1]
    assert captured_uris == ["spotify:track:t2"]

    log = session.exec(select(SyncLog)).first()
    assert log.status == "success"
    assert log.track_count == 1


# ────────────────────────────────────────────────────────────
# (e) blacklist drains all candidates — no error
# ────────────────────────────────────────────────────────────

def test_run_sync_completes_when_blacklist_drains_candidates(session):
    session.add(Playlist(user_id=1, spotify_id="pl1", name="Mix", is_included=True))
    _user = session.exec(select(User)).first()
    _user.playlist_size = 50
    session.add(_user)
    session.add(TrackBlacklist(user_id=1, spotify_id="t1", blacklisted_at="2026-05-20T00:00:00Z"))
    session.add(TrackBlacklist(user_id=1, spotify_id="t2", blacklisted_at="2026-05-20T00:00:00Z"))
    session.commit()

    mock_sp = MagicMock()
    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch("services.sync_engine.spotify_service.get_playlist_tracks", return_value=PLAYLIST_TRACKS),
        patch("services.sync_engine.spotify_service.get_or_create_dynamic_playlist", return_value="dyn_id"),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks") as mock_replace,
    ):
        result = sync_engine.run_sync(1)

    assert result == {"status": "success", "track_count": 0, "new_track_count": 0}
    captured_uris = mock_replace.call_args[0][1]
    assert captured_uris == []

    log = session.exec(select(SyncLog)).first()
    assert log.status == "success"
    assert log.track_count == 0


# ────────────────────────────────────────────────────────────
# (f) delta path — blacklisted existing track is removed
# ────────────────────────────────────────────────────────────

def test_run_sync_delta_path_excludes_blacklisted_existing_track(session):
    session.add(Playlist(user_id=1, spotify_id="pl1", name="Mix", is_included=True))
    _user = session.exec(select(User)).first()
    _user.playlist_size = 10
    _user.last_sync_at = "2026-05-19T00:00:00Z"
    session.add(_user)
    session.add(TrackBlacklist(user_id=1, spotify_id="old_track", blacklisted_at="2026-05-20T00:00:00Z"))
    session.commit()

    existing = [
        {
            "spotify_id": "old_track",
            "uri": "spotify:track:old_track",
            "added_at": "2026-05-15T00:00:00Z",
        }
    ]
    new_from_source = [
        {
            "spotify_id": "new_track",
            "uri": "spotify:track:new_track",
            "added_at": "2026-05-20T00:00:00Z",
        }
    ]

    def get_tracks(playlist_id, sp, since=None):
        if playlist_id == "dyn_id":
            return existing
        return new_from_source

    mock_sp = MagicMock()
    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch("services.sync_engine.spotify_service.get_playlist_tracks", side_effect=get_tracks),
        patch("services.sync_engine.spotify_service.get_or_create_dynamic_playlist", return_value="dyn_id"),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks") as mock_replace,
    ):
        sync_engine.run_sync(1)

    captured_uris = mock_replace.call_args[0][1]
    assert captured_uris == ["spotify:track:new_track"]


# ────────────────────────────────────────────────────────────
# (g) deleting a blacklist row restores the track on next sync
# ────────────────────────────────────────────────────────────

def test_run_sync_restores_track_after_blacklist_delete(session):
    session.add(Playlist(user_id=1, spotify_id="pl1", name="Mix", is_included=True))
    _user = session.exec(select(User)).first()
    _user.playlist_size = 2
    session.add(_user)
    row = TrackBlacklist(spotify_id="t1", user_id=_user.id, blacklisted_at="2026-05-20T00:00:00Z")
    session.add(row)
    session.commit()

    mock_sp = MagicMock()
    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch("services.sync_engine.spotify_service.get_playlist_tracks", return_value=PLAYLIST_TRACKS),
        patch("services.sync_engine.spotify_service.get_or_create_dynamic_playlist", return_value="dyn_id"),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks") as mock_replace,
    ):
        sync_engine.run_sync(1)
        first_uris = mock_replace.call_args[0][1]
    assert first_uris == ["spotify:track:t2"]

    blacklisted = session.exec(select(TrackBlacklist)).first()
    session.delete(blacklisted)
    session.commit()

    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch("services.sync_engine.spotify_service.get_playlist_tracks", return_value=PLAYLIST_TRACKS),
        patch("services.sync_engine.spotify_service.get_or_create_dynamic_playlist", return_value="dyn_id"),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks") as mock_replace,
    ):
        sync_engine.run_sync(1)
        second_uris = mock_replace.call_args[0][1]
    assert second_uris == ["spotify:track:t1", "spotify:track:t2"]
