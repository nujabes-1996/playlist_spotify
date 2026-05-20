from typing import Optional

from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from dependencies import SessionDep
from models.config import Config
from scheduler import bootstrap_scheduler

router = APIRouter(tags=["config"])


def _validate_cron(cron_expr: str | None) -> None:
    if not cron_expr:
        return
    try:
        CronTrigger.from_crontab(cron_expr)
    except (ValueError, KeyError):
        raise HTTPException(status_code=400, detail="Invalid cron expression")


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


class ConfigPatch(BaseModel):
    playlist_size: Optional[int] = None
    cron_expr: Optional[str] = None


@router.patch("/config", response_model=ConfigRead)
def patch_config(payload: ConfigPatch, session: SessionDep) -> ConfigRead:
    config = session.exec(select(Config)).first()
    if config is None:
        raise HTTPException(status_code=400, detail="Setup required before updating config")
    cron_changed = "cron_expr" in payload.model_fields_set
    if payload.playlist_size is not None:
        config.playlist_size = payload.playlist_size
    if cron_changed:
        _validate_cron(payload.cron_expr)
        config.cron_expr = payload.cron_expr or None
    session.commit()
    session.refresh(config)
    if cron_changed:
        bootstrap_scheduler(config.cron_expr)
    return ConfigRead(
        setup_required=not bool(config.client_id),
        playlist_size=config.playlist_size,
        cron_expr=config.cron_expr,
    )


@router.put("/config", response_model=ConfigRead)
def update_config(payload: ConfigWrite, session: SessionDep) -> ConfigRead:
    config = session.exec(select(Config)).first()
    if config is None:
        config = Config()
        session.add(config)
    _validate_cron(payload.cron_expr)
    config.client_id = payload.client_id
    config.client_secret = payload.client_secret
    config.playlist_size = payload.playlist_size if payload.playlist_size is not None else 50
    config.cron_expr = payload.cron_expr or None
    session.commit()
    session.refresh(config)
    bootstrap_scheduler(config.cron_expr)
    return ConfigRead(
        setup_required=not bool(config.client_id),
        playlist_size=config.playlist_size,
        cron_expr=config.cron_expr,
    )
