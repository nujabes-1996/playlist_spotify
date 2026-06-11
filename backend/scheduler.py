from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session, select

from database import engine
from models.user import User

DATABASE_URL = "sqlite:////data/app.db"

scheduler = BackgroundScheduler(
    jobstores={
        "default": SQLAlchemyJobStore(url=DATABASE_URL)
    }
)


def bootstrap_user_job(user_id: int, cron_expr: str | None) -> None:
    """Register (or remove) the per-user sync job `sync_{user_id}`.

    With a cron_expr, schedule run_sync for this user, passing the user id as the job
    argument (the SQLAlchemyJobStore pickles args, so we pass a stable int — never a
    User ORM instance). With no cron_expr, remove the user's job if it exists.
    """
    from services.sync_engine import run_sync  # local import to avoid circular dependency

    job_id = f"sync_{user_id}"
    if cron_expr:
        scheduler.add_job(
            run_sync,
            CronTrigger.from_crontab(cron_expr),
            id=job_id,
            args=[user_id],
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    else:
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)


def bootstrap_all_jobs() -> None:
    """Reconcile per-user jobs against the DB.

    Registers a job for every user with a cron_expr and removes the job of any user who
    has cleared their cron. Idempotent (replace_existing=True), so it is safe to run on
    every startup.
    """
    with Session(engine) as session:
        users = session.exec(select(User)).all()
    for user in users:
        bootstrap_user_job(user.id, user.cron_expr)


def purge_legacy_global_job() -> None:
    """Remove the pre-10.4 global `sync_job` from the persisted store (upgrade safety).

    A prod DB upgraded from before per-user jobs still holds a persisted `sync_job` that
    would call run_sync with no args (TypeError) and double-run the owner's sync. Drop it
    so only the new per-user jobs remain.
    """
    if scheduler.get_job("sync_job"):
        scheduler.remove_job("sync_job")
