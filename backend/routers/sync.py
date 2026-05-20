import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import select

import services.sync_engine as sync_engine
from dependencies import SessionDep
from models.sync_log import SyncLog

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/logs")
def get_sync_logs(session: SessionDep) -> list[SyncLog]:
    logs = session.exec(
        select(SyncLog).order_by(SyncLog.timestamp.desc())
    ).all()
    return list(logs)


@router.get("/status")
def get_sync_status(session: SessionDep) -> SyncLog | None:
    return session.exec(
        select(SyncLog).order_by(SyncLog.timestamp.desc())
    ).first()


@router.post("/run")
def run_sync() -> dict:
    try:
        return sync_engine.run_sync()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _run_sync_stream():
    """Async generator that runs the full sync pipeline and yields SSE events."""
    from datetime import datetime
    from sqlmodel import Session, select as sa_select
    from database import engine
    from models.config import Config
    from models.playlist import Playlist
    import services.spotify as spotify_service
    from services.sync_engine import harvest_tracks, deduplicate, sort_and_slice, _write_sync_log

    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        yield _sse("sync_log", {"level": "info", "message": "Starting sync…", "timestamp": timestamp})

        with Session(engine) as session:
            playlists = session.exec(
                sa_select(Playlist).where(Playlist.is_included == True)  # noqa: E712
            ).all()
            if not playlists:
                raise ValueError("No playlists selected")
            config = session.exec(sa_select(Config)).first()
            playlist_size = config.playlist_size if config else 50

        yield _sse("sync_log", {"level": "info", "message": f"Found {len(playlists)} included playlist(s)", "timestamp": timestamp})

        sp = await asyncio.to_thread(spotify_service.get_authenticated_client)
        raw_tracks = await asyncio.to_thread(harvest_tracks, playlists, sp)

        yield _sse("sync_log", {"level": "info", "message": f"Harvested {len(raw_tracks)} tracks", "timestamp": timestamp})

        deduped = deduplicate(raw_tracks)
        sliced = sort_and_slice(deduped, playlist_size)

        yield _sse("sync_log", {"level": "info", "message": f"After dedup/sort: {len(sliced)} tracks", "timestamp": timestamp})

        target_id = await asyncio.to_thread(spotify_service.get_or_create_dynamic_playlist, sp)
        track_uris = [t["uri"] for t in sliced]
        await asyncio.to_thread(spotify_service.replace_playlist_tracks, target_id, track_uris, sp)

        _write_sync_log("success", len(sliced), None, timestamp)
        yield _sse("sync_complete", {"status": "success", "track_count": len(sliced), "timestamp": timestamp})

    except Exception as exc:
        _write_sync_log("failure", None, str(exc), timestamp)
        yield _sse("sync_error", {"status": "error", "message": str(exc), "timestamp": timestamp})


@router.get("/stream")
async def stream_sync():
    return StreamingResponse(
        _run_sync_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
