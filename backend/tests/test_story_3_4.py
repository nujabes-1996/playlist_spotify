import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool

from models.config import Config
from models.playlist import Playlist
from models.sync_log import SyncLog
import services.sync_engine as sync_engine
import services.spotify as spotify_service_module


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


# ────────────────────────────────────────────────────────────
# Tests for get_or_create_dynamic_playlist
# ────────────────────────────────────────────────────────────

def test_get_or_create_uses_stored_id(session):
    session.add(Config(playlist_size=50, dynamic_playlist_id="existing_id"))
    session.commit()

    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {"id": "existing_id"}

    with patch("services.spotify.engine", session.get_bind()):
        result = spotify_service_module.get_or_create_dynamic_playlist(mock_sp)

    assert result == "existing_id"
    mock_sp.user_playlist_create.assert_not_called()


def test_get_or_create_creates_when_no_stored_id(session):
    session.add(Config(playlist_size=50, dynamic_playlist_id=None))
    session.commit()

    mock_sp = MagicMock()
    mock_sp.me.return_value = {"id": "user123"}
    mock_sp.current_user_playlists.return_value = {"items": [], "next": None}
    mock_sp.current_user_playlist_create.return_value = {"id": "new_playlist_id"}

    with patch("services.spotify.engine", session.get_bind()):
        result = spotify_service_module.get_or_create_dynamic_playlist(mock_sp)

    assert result == "new_playlist_id"
    mock_sp.current_user_playlist_create.assert_called_once()
    config = session.exec(select(Config)).first()
    assert config.dynamic_playlist_id == "new_playlist_id"


def test_get_or_create_recreates_on_invalid_stored_id(session):
    session.add(Config(playlist_size=50, dynamic_playlist_id="stale_id"))
    session.commit()

    mock_sp = MagicMock()
    mock_sp.playlist.side_effect = Exception("404 Not Found")
    mock_sp.me.return_value = {"id": "user123"}
    mock_sp.current_user_playlists.return_value = {"items": [], "next": None}
    mock_sp.current_user_playlist_create.return_value = {"id": "new_id"}

    with patch("services.spotify.engine", session.get_bind()):
        result = spotify_service_module.get_or_create_dynamic_playlist(mock_sp)

    assert result == "new_id"
    mock_sp.current_user_playlist_create.assert_called_once()


# ────────────────────────────────────────────────────────────
# Tests for replace_playlist_tracks
# ────────────────────────────────────────────────────────────

def test_replace_tracks_single_batch():
    mock_sp = MagicMock()
    uris = [f"spotify:track:{i}" for i in range(50)]
    spotify_service_module.replace_playlist_tracks("pl1", uris, mock_sp)
    mock_sp.playlist_replace_items.assert_called_once_with("pl1", uris)
    mock_sp.playlist_add_items.assert_not_called()


def test_replace_tracks_chunked():
    mock_sp = MagicMock()
    uris = [f"spotify:track:{i}" for i in range(150)]
    spotify_service_module.replace_playlist_tracks("pl1", uris, mock_sp)
    mock_sp.playlist_replace_items.assert_called_once_with("pl1", uris[:100])
    mock_sp.playlist_add_items.assert_called_once_with("pl1", uris[100:150])


# ────────────────────────────────────────────────────────────
# Integration tests for run_sync()
# ────────────────────────────────────────────────────────────

PLAYLIST_A = [
    {"spotify_id": "t1", "uri": "spotify:track:t1", "added_at": "2026-05-10T00:00:00Z"},
    {"spotify_id": "t2", "uri": "spotify:track:t2", "added_at": "2026-05-08T00:00:00Z"},
]


def test_run_sync_success_writes_log(session):
    session.add(Playlist(spotify_id="pl1", name="Mix", is_included=True))
    session.add(Config(playlist_size=2, dynamic_playlist_id="dyn_id"))
    session.commit()

    mock_sp = MagicMock()
    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch("services.sync_engine.spotify_service.get_playlist_tracks", return_value=PLAYLIST_A),
        patch("services.sync_engine.spotify_service.get_or_create_dynamic_playlist", return_value="dyn_id"),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks"),
    ):
        sync_engine.run_sync()

    logs = session.exec(select(SyncLog)).all()
    assert len(logs) == 1
    assert logs[0].status == "success"
    assert logs[0].track_count == 2
    assert logs[0].error_message is None
    assert logs[0].timestamp.endswith("Z")


def test_run_sync_success_returns_dict(session):
    session.add(Playlist(spotify_id="pl1", name="Mix", is_included=True))
    session.add(Config(playlist_size=50, dynamic_playlist_id="dyn_id"))
    session.commit()

    mock_sp = MagicMock()
    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch("services.sync_engine.spotify_service.get_playlist_tracks", return_value=PLAYLIST_A),
        patch("services.sync_engine.spotify_service.get_or_create_dynamic_playlist", return_value="dyn_id"),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks"),
    ):
        result = sync_engine.run_sync()

    assert result["status"] == "success"
    assert result["track_count"] == 2
    assert "new_track_count" in result


def test_run_sync_no_playlists_writes_failure_log(session):
    session.add(Config(playlist_size=50))
    session.commit()

    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks") as mock_replace,
    ):
        with pytest.raises(ValueError, match="No playlists selected"):
            sync_engine.run_sync()
        mock_replace.assert_not_called()

    logs = session.exec(select(SyncLog)).all()
    assert len(logs) == 1
    assert logs[0].status == "failure"
    assert "No playlists selected" in logs[0].error_message


def test_run_sync_spotify_error_writes_failure_log(session):
    session.add(Playlist(spotify_id="pl1", name="Mix", is_included=True))
    session.add(Config(playlist_size=50, dynamic_playlist_id="dyn_id"))
    session.commit()

    mock_sp = MagicMock()
    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch("services.sync_engine.spotify_service.get_playlist_tracks", return_value=PLAYLIST_A),
        patch("services.sync_engine.spotify_service.get_or_create_dynamic_playlist", return_value="dyn_id"),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks", side_effect=Exception("Spotify 500")),
    ):
        with pytest.raises(Exception, match="Spotify 500"):
            sync_engine.run_sync()

    logs = session.exec(select(SyncLog)).all()
    assert len(logs) == 1
    assert logs[0].status == "failure"
    assert "Spotify 500" in logs[0].error_message


def test_run_sync_preserves_playlist_on_harvest_error(session):
    session.add(Playlist(spotify_id="pl1", name="Mix", is_included=True))
    session.add(Config(playlist_size=50, dynamic_playlist_id="dyn_id"))
    session.commit()

    mock_sp = MagicMock()
    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch("services.sync_engine.spotify_service.get_playlist_tracks", side_effect=Exception("Token error")),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks") as mock_replace,
    ):
        with pytest.raises(Exception):
            sync_engine.run_sync()

    mock_replace.assert_not_called()  # Playlist untouched (NFR10)
