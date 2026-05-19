import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

import models  # noqa: F401 — side-effect import registers all table metadata
from database import engine
from routers.auth import router as auth_router
from routers.config import router as config_router
from scheduler import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    scheduler.start()
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


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
