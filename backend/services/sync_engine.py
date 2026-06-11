from datetime import datetime

import services.blacklist_service as blacklist_service
import services.spotify as spotify_service
from sqlmodel import Session, select

from database import engine
from models.playlist import Playlist
from models.sync_log import SyncLog
from models.user import User


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
    user_id: int | None = None,
) -> None:
    with Session(engine) as session:
        session.add(
            SyncLog(
                user_id=user_id,
                status=status,
                track_count=track_count,
                new_track_count=new_track_count,
                error_message=error_message,
                timestamp=timestamp,
            )
        )
        session.commit()


def run_sync(user_id: int) -> dict:
    """
    Full sync pipeline for one user: harvest → dedup → sort → slice → push → log.

    Each user's scheduled job (and the manual POST /sync/run) calls this with that
    user's id; the User row is re-loaded by id here (the background job has no request
    session). Returns a skip dict if the user no longer exists.

    On first run (no last_sync_at): full fetch from all selected playlists.
    On subsequent runs: fetches only tracks added since last_sync_at, merges
    with the current Recent Adds content, then re-sorts and slices to playlist_size.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    with Session(engine) as session:
        user = session.get(User, user_id)
    if user is None:
        return {"status": "skipped", "reason": "user not found"}

    try:
        with Session(engine) as session:
            playlists = session.exec(
                select(Playlist).where(
                    Playlist.user_id == user.id,
                    Playlist.is_included == True,  # noqa: E712
                    Playlist.is_hidden == False,  # noqa: E712
                )
            ).all()
            if not playlists:
                raise ValueError("No playlists selected")
            playlist_size = user.playlist_size
            last_sync_at = user.last_sync_at
            blacklisted_ids = blacklist_service.get_blacklisted_ids(session, user.id)

        sp = spotify_service.get_authenticated_client(user)
        target_id = spotify_service.get_or_create_dynamic_playlist(sp, user)
        existing_tracks = spotify_service.get_playlist_tracks(target_id, sp)
        existing_ids = {t["spotify_id"] for t in existing_tracks}

        if last_sync_at:
            new_tracks = harvest_tracks(playlists, sp, since=last_sync_at)
            raw_tracks = new_tracks + existing_tracks
        else:
            raw_tracks = harvest_tracks(playlists, sp)

        deduped = deduplicate(raw_tracks)
        filtered = [t for t in deduped if t["spotify_id"] not in blacklisted_ids]

        # Delta sync can't backfill: if we're below the target (e.g. user raised
        # playlist_size, or tracks were blacklisted), do a full harvest to top up.
        if last_sync_at and len(filtered) < playlist_size:
            full_tracks = harvest_tracks(playlists, sp)
            deduped = deduplicate(full_tracks + existing_tracks)
            filtered = [t for t in deduped if t["spotify_id"] not in blacklisted_ids]
        sliced = sort_and_slice(filtered, playlist_size)
        new_track_count = sum(1 for t in sliced if t["spotify_id"] not in existing_ids)

        track_uris = [t["uri"] for t in sliced]
        spotify_service.replace_playlist_tracks(target_id, track_uris, sp)

        with Session(engine) as session:
            db_user = session.get(User, user.id)
            if db_user:
                db_user.last_sync_at = timestamp
                session.add(db_user)
                session.commit()

        _write_sync_log(
            status="success",
            track_count=len(sliced),
            new_track_count=new_track_count,
            error_message=None,
            timestamp=timestamp,
            user_id=user.id,
        )
        return {"status": "success", "track_count": len(sliced), "new_track_count": new_track_count}

    except Exception as exc:
        _write_sync_log(
            status="failure",
            track_count=None,
            new_track_count=None,
            error_message=str(exc),
            timestamp=timestamp,
            user_id=user.id,
        )
        raise
