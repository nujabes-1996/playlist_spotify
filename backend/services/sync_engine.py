from datetime import datetime

import services.spotify as spotify_service
from sqlmodel import Session, select

from database import engine
from models.config import Config
from models.playlist import Playlist
from models.sync_log import SyncLog


def harvest_tracks(included_playlists: list, sp, since: str | None = None) -> list[dict]:
    """Fetch tracks from all included playlists. When since is set, only returns new tracks."""
    all_tracks = []
    for playlist in included_playlists:
        tracks = spotify_service.get_playlist_tracks(playlist.spotify_id, sp, since=since)
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
    new_track_count: int | None,
    error_message: str | None,
    timestamp: str,
) -> None:
    with Session(engine) as session:
        session.add(
            SyncLog(
                status=status,
                track_count=track_count,
                new_track_count=new_track_count,
                error_message=error_message,
                timestamp=timestamp,
            )
        )
        session.commit()


def run_sync() -> dict:
    """
    Full sync pipeline: harvest → dedup → sort → slice → push → log.

    On first run (no last_sync_at): full fetch from all selected playlists.
    On subsequent runs: fetches only tracks added since last_sync_at, merges
    with the current Recent Adds content, then re-sorts and slices to playlist_size.
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
            last_sync_at = config.last_sync_at if config else None

        sp = spotify_service.get_authenticated_client()
        target_id = spotify_service.get_or_create_dynamic_playlist(sp)
        existing_tracks = spotify_service.get_playlist_tracks(target_id, sp)
        existing_ids = {t["spotify_id"] for t in existing_tracks}

        if last_sync_at:
            new_tracks = harvest_tracks(playlists, sp, since=last_sync_at)
            raw_tracks = new_tracks + existing_tracks
        else:
            raw_tracks = harvest_tracks(playlists, sp)

        deduped = deduplicate(raw_tracks)
        sliced = sort_and_slice(deduped, playlist_size)
        new_track_count = sum(1 for t in sliced if t["spotify_id"] not in existing_ids)

        track_uris = [t["uri"] for t in sliced]
        spotify_service.replace_playlist_tracks(target_id, track_uris, sp)

        with Session(engine) as session:
            config = session.exec(select(Config)).first()
            if config:
                config.last_sync_at = timestamp
                session.add(config)
                session.commit()

        _write_sync_log(
            status="success",
            track_count=len(sliced),
            new_track_count=new_track_count,
            error_message=None,
            timestamp=timestamp,
        )
        return {"status": "success", "track_count": len(sliced), "new_track_count": new_track_count}

    except Exception as exc:
        _write_sync_log(
            status="failure",
            track_count=None,
            new_track_count=None,
            error_message=str(exc),
            timestamp=timestamp,
        )
        raise
