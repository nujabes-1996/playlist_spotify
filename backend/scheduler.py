from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

DATABASE_URL = "sqlite:////data/app.db"

scheduler = BackgroundScheduler(
    jobstores={
        "default": SQLAlchemyJobStore(url=DATABASE_URL)
    }
)
