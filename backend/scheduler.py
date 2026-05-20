from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger

DATABASE_URL = "sqlite:////data/app.db"

scheduler = BackgroundScheduler(
    jobstores={
        "default": SQLAlchemyJobStore(url=DATABASE_URL)
    }
)


def bootstrap_scheduler(cron_expr: str | None) -> None:
    from services.sync_engine import run_sync  # local import to avoid circular dependency

    if cron_expr:
        scheduler.add_job(
            run_sync,
            CronTrigger.from_crontab(cron_expr),
            id="sync_job",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    else:
        if scheduler.get_job("sync_job"):
            scheduler.remove_job("sync_job")
