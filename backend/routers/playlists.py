from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from dependencies import SessionDep
from models.playlist import Playlist
from services import spotify as spotify_service

router = APIRouter(tags=["playlists"])


class PlaylistRead(BaseModel):
    spotify_id: str
    name: str
    is_included: bool


class PlaylistPatch(BaseModel):
    is_included: bool


@router.get("/playlists", response_model=list[PlaylistRead])
def get_playlists(session: SessionDep) -> list[PlaylistRead]:
    try:
        spotify_playlists = spotify_service.get_user_playlists()
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    spotify_ids = {p["spotify_id"] for p in spotify_playlists}

    # Upsert: add new rows, update name of existing
    for p in spotify_playlists:
        existing = session.exec(
            select(Playlist).where(Playlist.spotify_id == p["spotify_id"])
        ).first()
        if existing:
            existing.name = p["name"]
        else:
            session.add(Playlist(spotify_id=p["spotify_id"], name=p["name"]))

    # Remove playlists no longer returned by Spotify
    db_playlists = session.exec(select(Playlist)).all()
    for db_p in db_playlists:
        if db_p.spotify_id not in spotify_ids:
            session.delete(db_p)

    session.commit()

    rows = session.exec(select(Playlist)).all()
    return [
        PlaylistRead(spotify_id=r.spotify_id, name=r.name, is_included=r.is_included)
        for r in rows
    ]


@router.patch("/playlists/{spotify_id}", response_model=PlaylistRead)
def toggle_playlist(
    spotify_id: str, payload: PlaylistPatch, session: SessionDep
) -> PlaylistRead:
    playlist = session.exec(
        select(Playlist).where(Playlist.spotify_id == spotify_id)
    ).first()
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    playlist.is_included = payload.is_included
    session.commit()
    session.refresh(playlist)
    return PlaylistRead(
        spotify_id=playlist.spotify_id,
        name=playlist.name,
        is_included=playlist.is_included,
    )
