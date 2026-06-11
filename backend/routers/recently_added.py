from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from spotipy import SpotifyException

from dependencies import CurrentUserDep
from services import spotify as spotify_service

router = APIRouter(tags=["recently-added"])


class RecentlyAddedTrack(BaseModel):
    spotify_id: str
    title: str
    artists: list[str]
    album: str
    image_url: str | None = None
    added_at: str
    duration_ms: int
    explicit: bool
    has_video: bool
    is_blacklisted: bool


@router.get("/recently-added", response_model=list[RecentlyAddedTrack])
def get_recently_added(current_user: CurrentUserDep) -> list[RecentlyAddedTrack]:
    try:
        tracks = spotify_service.get_recently_added_tracks(current_user)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except SpotifyException as exc:
        raise HTTPException(status_code=502, detail=f"Spotify error: {exc.msg}")
    return [RecentlyAddedTrack(**t) for t in tracks]
