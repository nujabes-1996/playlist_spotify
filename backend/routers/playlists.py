from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from spotipy import SpotifyException
from sqlmodel import select

from dependencies import CurrentUserDep, SessionDep
from models.playlist import Playlist
from services import spotify as spotify_service

router = APIRouter(tags=["playlists"])


class PlaylistRead(BaseModel):
    spotify_id: str
    name: str
    is_included: bool
    is_hidden: bool
    image_url: Optional[str] = None
    track_count: Optional[int] = None


class PlaylistPatch(BaseModel):
    is_included: Optional[bool] = None
    is_hidden: Optional[bool] = None


class PlaylistTrack(BaseModel):
    spotify_id: str
    title: str
    artists: list[str]
    album: str
    image_url: Optional[str] = None
    added_at: str
    duration_ms: int
    explicit: bool
    has_video: bool
    is_blacklisted: bool


@router.get("/playlists", response_model=list[PlaylistRead])
def get_playlists(session: SessionDep, current_user: CurrentUserDep) -> list[PlaylistRead]:
    try:
        spotify_playlists = spotify_service.get_user_playlists(current_user)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    spotify_ids = {p["spotify_id"] for p in spotify_playlists}
    meta_map = {
        p["spotify_id"]: (p.get("image_url"), p.get("track_count"))
        for p in spotify_playlists
    }

    # Upsert: add new rows, update name of existing (scoped to current user)
    for p in spotify_playlists:
        existing = session.exec(
            select(Playlist).where(
                Playlist.user_id == current_user.id,
                Playlist.spotify_id == p["spotify_id"],
            )
        ).first()
        if existing:
            existing.name = p["name"]
        else:
            session.add(
                Playlist(
                    user_id=current_user.id,
                    spotify_id=p["spotify_id"],
                    name=p["name"],
                )
            )

    # Remove this user's playlists no longer returned by Spotify
    db_playlists = session.exec(
        select(Playlist).where(Playlist.user_id == current_user.id)
    ).all()
    for db_p in db_playlists:
        if db_p.spotify_id not in spotify_ids:
            session.delete(db_p)

    session.commit()

    rows = session.exec(
        select(Playlist).where(Playlist.user_id == current_user.id)
    ).all()
    result = []
    for r in rows:
        image_url, track_count = meta_map.get(r.spotify_id, (None, None))
        result.append(
            PlaylistRead(
                spotify_id=r.spotify_id,
                name=r.name,
                is_included=r.is_included,
                is_hidden=r.is_hidden,
                image_url=image_url,
                track_count=track_count,
            )
        )
    return result


class PlaylistTracksPage(BaseModel):
    items: list[PlaylistTrack]
    next_offset: Optional[int]
    total: int


@router.get("/playlists/{spotify_id}/tracks", response_model=PlaylistTracksPage)
def get_playlist_tracks(
    spotify_id: str,
    current_user: CurrentUserDep,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PlaylistTracksPage:
    try:
        page = spotify_service.get_playlist_tracks_page(spotify_id, limit, offset, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except SpotifyException as exc:
        if exc.http_status == 404:
            raise HTTPException(status_code=404, detail="Playlist not found")
        raise HTTPException(status_code=502, detail=f"Spotify error: {exc.msg}")
    return PlaylistTracksPage(**page)


@router.patch("/playlists/{spotify_id}", response_model=PlaylistRead)
def toggle_playlist(
    spotify_id: str,
    payload: PlaylistPatch,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> PlaylistRead:
    playlist = session.exec(
        select(Playlist).where(
            Playlist.user_id == current_user.id,
            Playlist.spotify_id == spotify_id,
        )
    ).first()
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")

    if payload.is_hidden is True:
        playlist.is_hidden = True
        playlist.is_included = False
    elif payload.is_hidden is False:
        playlist.is_hidden = False

    if payload.is_included is not None:
        playlist.is_included = payload.is_included

    session.commit()
    session.refresh(playlist)
    return PlaylistRead(
        spotify_id=playlist.spotify_id,
        name=playlist.name,
        is_included=playlist.is_included,
        is_hidden=playlist.is_hidden,
        image_url=None,
        track_count=None,
    )
