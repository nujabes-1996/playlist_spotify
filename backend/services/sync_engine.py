from datetime import datetime

import services.spotify as spotify_service
from sqlmodel import Session, select

from database import engine
from models.config import Config
from models.playlist import Playlist
from models.sync_log import SyncLog


def harvest_tracks(included_playlists: list, sp) -> list[dict]:
    """Fetch all tracks from all included playlists. Returns flat list of {spotify_id, uri, added_at}."""
    all_tracks = []
    for playlist in included_playlists:
        tracks = spotify_service.get_playlist_tracks(playlist.spotify_id, sp)
        all_tracks.extend(tracks)
    return all_tracks


def deduplicate(tracks: list[dict]) -> list[dict]:
    """Keep one entry per spotify_id — the one with the most recent added_at."""
    best: dict[str, dict] = {}
    for track in tracks:
        tid = track["spotify_id"]
        if tid not in best or track["added_at"] > best[tid]["added_at"]:
            best[tid] = track
    return list(best.values())


def sort_and_slice(tracks: list[dict], playlist_size: int) -> list[dict]:
    """Sort by added_at descending, return top playlist_size tracks."""
    sorted_tracks = sorted(tracks, key=lambda t: t["added_at"], reverse=True)
    return sorted_tracks[:playlist_size]


def _write_sync_log(
    status: str,
    track_count: int | None,
    error_message: str | None,
    timestamp: str,
) -> None:
    with Session(engine) as session:
        session.add(
            SyncLog(
                status=status,
                track_count=track_count,
                error_message=error_message,
                timestamp=timestamp,
            )
        )
        session.commit()


def run_sync() -> dict:
    """
    Full sync pipeline: harvest → dedup → sort → slice → push → log.
    Returns {"status": "success", "track_count": N} on success.
    On failure: writes SyncLog with status="failure" and re-raises the exception.
    Existing dynamic playlist is preserved on any error (NFR10).
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        with Session(engine) as session:
            playlists = session.exec(
                select(Playlist).where(Playlist.is_included == True)  # noqa: E712
            ).all()
            if not playlists:
                raise ValueError("No playlists selected")
            config = session.exec(select(Config)).first()
            playlist_size = config.playlist_size if config else 50

        sp = spotify_service.get_authenticated_client()
        raw_tracks = harvest_tracks(playlists, sp)
        deduped = deduplicate(raw_tracks)
        sliced = sort_and_slice(deduped, playlist_size)

        # Push to Spotify — only reached if harvest/dedup/sort succeeded (NFR10)
        target_id = spotify_service.get_or_create_dynamic_playlist(sp)
        track_uris = [t["uri"] for t in sliced]
        spotify_service.replace_playlist_tracks(target_id, track_uris, sp)

        _write_sync_log(
            status="success",
            track_count=len(sliced),
            error_message=None,
            timestamp=timestamp,
        )
        return {"status": "success", "track_count": len(sliced)}

    except Exception as exc:
        _write_sync_log(
            status="failure",
            track_count=None,
            error_message=str(exc),
            timestamp=timestamp,
        )
        raise
