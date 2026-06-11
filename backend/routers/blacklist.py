from datetime import datetime

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field
from sqlmodel import select

from dependencies import CurrentUserDep, SessionDep
from models.track_blacklist import TrackBlacklist

router = APIRouter(tags=["blacklist"])


class BlacklistRead(BaseModel):
    spotify_id: str
    blacklisted_at: str


class BlacklistCreate(BaseModel):
    spotify_id: str = Field(..., min_length=1)


@router.get("/blacklist", response_model=list[BlacklistRead])
def get_blacklist(session: SessionDep, current_user: CurrentUserDep) -> list[BlacklistRead]:
    rows = session.exec(
        select(TrackBlacklist)
        .where(TrackBlacklist.user_id == current_user.id)
        .order_by(TrackBlacklist.blacklisted_at.desc())
    ).all()
    return [
        BlacklistRead(spotify_id=r.spotify_id, blacklisted_at=r.blacklisted_at)
        for r in rows
    ]


@router.post("/blacklist", response_model=BlacklistRead)
def add_to_blacklist(
    payload: BlacklistCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
    response: Response,
) -> BlacklistRead:
    existing = session.exec(
        select(TrackBlacklist).where(
            TrackBlacklist.user_id == current_user.id,
            TrackBlacklist.spotify_id == payload.spotify_id,
        )
    ).first()
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return BlacklistRead(
            spotify_id=existing.spotify_id, blacklisted_at=existing.blacklisted_at
        )

    row = TrackBlacklist(
        spotify_id=payload.spotify_id,
        user_id=current_user.id,
        blacklisted_at=datetime.utcnow().isoformat(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    response.status_code = status.HTTP_201_CREATED
    return BlacklistRead(spotify_id=row.spotify_id, blacklisted_at=row.blacklisted_at)


@router.delete("/blacklist/{spotify_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_blacklist(
    spotify_id: str, session: SessionDep, current_user: CurrentUserDep
) -> Response:
    row = session.exec(
        select(TrackBlacklist).where(
            TrackBlacklist.user_id == current_user.id,
            TrackBlacklist.spotify_id == spotify_id,
        )
    ).first()
    if row is not None:
        session.delete(row)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
