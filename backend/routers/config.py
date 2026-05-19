from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import select

from dependencies import SessionDep
from models.config import Config

router = APIRouter(tags=["config"])


class ConfigRead(BaseModel):
    setup_required: bool
    playlist_size: int
    cron_expr: Optional[str]


class ConfigWrite(BaseModel):
    client_id: str
    client_secret: str
    playlist_size: Optional[int] = 50
    cron_expr: Optional[str] = None


@router.get("/config", response_model=ConfigRead)
def get_config(session: SessionDep) -> ConfigRead:
    config = session.exec(select(Config)).first()
    if config is None or not config.client_id:
        return ConfigRead(setup_required=True, playlist_size=50, cron_expr=None)
    return ConfigRead(
        setup_required=False,
        playlist_size=config.playlist_size,
        cron_expr=config.cron_expr,
    )


@router.put("/config", response_model=ConfigRead)
def update_config(payload: ConfigWrite, session: SessionDep) -> ConfigRead:
    config = session.exec(select(Config)).first()
    if config is None:
        config = Config()
        session.add(config)
    config.client_id = payload.client_id
    config.client_secret = payload.client_secret
    config.playlist_size = payload.playlist_size if payload.playlist_size is not None else 50
    config.cron_expr = payload.cron_expr
    session.commit()
    session.refresh(config)
    return ConfigRead(
        setup_required=not bool(config.client_id),
        playlist_size=config.playlist_size,
        cron_expr=config.cron_expr,
    )
