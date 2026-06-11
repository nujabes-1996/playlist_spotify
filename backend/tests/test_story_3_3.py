import pytest
from unittest.mock import patch, MagicMock
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from sqlmodel import select
from models.playlist import Playlist
from models.user import User
import services.sync_engine as sync_engine


@pytest.fixture(name="session")
def session_fixture():
    test_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        # Story 10.2: scheduled sync resolves the single logged-in user
        session.add(User(spotify_user_id="scheduled", client_id="c", client_secret="s", token_json="{}"))
        session.commit()
        yield session


PLAYLIST_A = [
    {"spotify_id": "t1", "uri": "spotify:track:t1", "added_at": "2026-05-10T00:00:00Z"},
    {"spotify_id": "t2", "uri": "spotify:track:t2", "added_at": "2026-05-08T00:00:00Z"},
]
PLAYLIST_B = [
    {"spotify_id": "t1", "uri": "spotify:track:t1", "added_at": "2026-05-15T00:00:00Z"},  # t1 newer here
    {"spotify_id": "t3", "uri": "spotify:track:t3", "added_at": "2026-05-01T00:00:00Z"},
]


# --- Unit tests for pure functions ---

def test_dedup_keeps_latest_added_at():
    """AC2 — Dedup keeps the entry with the most recent added_at for a given spotify_id."""
    tracks = PLAYLIST_A + PLAYLIST_B  # t1 appears twice
    result = sync_engine.deduplicate(tracks)
    by_id = {t["spotify_id"]: t for t in result}
    assert by_id["t1"]["added_at"] == "2026-05-15T00:00:00Z"  # latest wins
    assert len(result) == 3  # t1, t2, t3


def test_dedup_no_collision():
    """Tracks with distinct spotify_ids are all preserved after dedup."""
    tracks = [
        {"spotify_id": "a", "uri": "spotify:track:a", "added_at": "2026-05-01T00:00:00Z"},
        {"spotify_id": "b", "uri": "spotify:track:b", "added_at": "2026-05-02T00:00:00Z"},
    ]
    result = sync_engine.deduplicate(tracks)
    assert len(result) == 2


def test_sort_and_slice_order():
    """AC3 — sort_and_slice returns tracks sorted by added_at descending."""
    tracks = [
        {"spotify_id": "a", "uri": "u", "added_at": "2026-05-01T00:00:00Z"},
        {"spotify_id": "b", "uri": "u", "added_at": "2026-05-10T00:00:00Z"},
        {"spotify_id": "c", "uri": "u", "added_at": "2026-05-05T00:00:00Z"},
    ]
    result = sync_engine.sort_and_slice(tracks, 10)
    assert result[0]["spotify_id"] == "b"
    assert result[1]["spotify_id"] == "c"
    assert result[2]["spotify_id"] == "a"


def test_sort_and_slice_respects_playlist_size():
    """AC4 — Only the top N tracks are returned."""
    tracks = [
        {"spotify_id": str(i), "uri": "u", "added_at": f"2026-05-{i:02d}T00:00:00Z"}
        for i in range(1, 11)
    ]
    result = sync_engine.sort_and_slice(tracks, 5)
    assert len(result) == 5


def test_harvest_collects_all_tracks():
    """AC1 — harvest_tracks collects all tracks from all playlists (pre-dedup)."""
    mock_playlists = [
        MagicMock(spotify_id="pl1"),
        MagicMock(spotify_id="pl2"),
    ]
    with patch(
        "services.sync_engine.spotify_service.get_playlist_tracks",
        side_effect=[PLAYLIST_A, PLAYLIST_B],
    ):
        result = sync_engine.harvest_tracks(mock_playlists, sp=MagicMock())
    assert len(result) == 4  # 2 + 2, duplicates NOT yet removed


# --- Integration tests for run_sync ---

def test_run_sync_no_playlists_raises(session):
    """AC6 — run_sync raises ValueError when no playlists are marked is_included=true."""
    with patch("services.sync_engine.engine", session.get_bind()):
        with pytest.raises(ValueError, match="No playlists selected"):
            sync_engine.run_sync(1)


def test_run_sync_returns_sliced_tracks(session):
    """AC1–AC4 — Happy path: harvest → dedup → sort → slice → push returns success dict."""
    session.add(Playlist(user_id=1, spotify_id="pl1", name="Mix", is_included=True))
    session.add(Playlist(user_id=1, spotify_id="pl2", name="Chill", is_included=True))
    user = session.exec(select(User)).first()
    user.playlist_size = 2
    session.add(user)
    session.commit()

    mock_sp = MagicMock()
    with (
        patch("services.sync_engine.engine", session.get_bind()),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch(
            "services.sync_engine.spotify_service.get_playlist_tracks",
            # 1st call: existing tracks in dynamic playlist (empty on first run)
            # 2nd call: pl1, 3rd call: pl2
            side_effect=[[], PLAYLIST_A, PLAYLIST_B],
        ),
        patch("services.sync_engine.spotify_service.get_or_create_dynamic_playlist", return_value="dyn_id"),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks"),
    ):
        result = sync_engine.run_sync(1)

    # playlist_size=2, all tracks are new (dynamic playlist was empty)
    assert result == {"status": "success", "track_count": 2, "new_track_count": 2}
