import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Session, select

import models  # noqa: F401 — side-effect import registers all table metadata
from database import engine
from models.config import Config
from routers.auth import router as auth_router
from routers.blacklist import router as blacklist_router
from routers.config import router as config_router
from routers.playlists import router as playlists_router
from routers.recently_added import router as recently_added_router
from routers.sync import router as sync_router
from scheduler import scheduler, bootstrap_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    scheduler.start()
    with Session(engine) as session:
        config = session.exec(select(Config)).first()
        bootstrap_scheduler(config.cron_expr if config else None)
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="playlist_spotify", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(playlists_router, prefix="/api/v1")
app.include_router(sync_router, prefix="/api/v1")
app.include_router(blacklist_router, prefix="/api/v1")
app.include_router(recently_added_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
