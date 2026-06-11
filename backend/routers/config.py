from typing import Optional

from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from dependencies import CurrentUserDep, SessionDep
from scheduler import bootstrap_user_job

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
    dynamic_playlist_id: Optional[str] = None


@router.get("/config", response_model=ConfigRead)
def get_config(current_user: CurrentUserDep) -> ConfigRead:
    # A session user always has credentials (login persists them), so setup is never
    # required for a gated request. Settings live on the user's own row.
    return ConfigRead(
        setup_required=not bool(current_user.client_id),
        playlist_size=current_user.playlist_size,
        cron_expr=current_user.cron_expr,
        dynamic_playlist_id=current_user.target_playlist_id,
    )


class ConfigPatch(BaseModel):
    playlist_size: Optional[int] = None
    cron_expr: Optional[str] = None


@router.patch("/config", response_model=ConfigRead)
def patch_config(
    payload: ConfigPatch, session: SessionDep, current_user: CurrentUserDep
) -> ConfigRead:
    cron_changed = "cron_expr" in payload.model_fields_set
    if payload.playlist_size is not None:
        current_user.playlist_size = payload.playlist_size
    if cron_changed:
        _validate_cron(payload.cron_expr)
        current_user.cron_expr = payload.cron_expr or None
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    if cron_changed:
        # Re-bootstrap only the acting user's job from their new cron_expr.
        bootstrap_user_job(current_user.id, current_user.cron_expr)
    return ConfigRead(
        setup_required=not bool(current_user.client_id),
        playlist_size=current_user.playlist_size,
        cron_expr=current_user.cron_expr,
        dynamic_playlist_id=current_user.target_playlist_id,
    )
