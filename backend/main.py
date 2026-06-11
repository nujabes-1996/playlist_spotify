import os
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlmodel import SQLModel

import models  # noqa: F401 — side-effect import registers all table metadata
from database import engine
from dependencies import get_current_user
from migrations import run_migrations
from routers.auth import router as auth_router
from routers.blacklist import router as blacklist_router
from routers.config import router as config_router
from routers.playlists import router as playlists_router
from routers.recently_added import router as recently_added_router
from routers.sync import router as sync_router
from scheduler import scheduler, bootstrap_all_jobs, purge_legacy_global_job


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_all first (guarantees the `user` table exists for FKs + builds the correct
    # fresh-install schema), then run_migrations to reshape/backfill legacy prod tables.
    SQLModel.metadata.create_all(engine)
    run_migrations(engine)
    scheduler.start()
    # Per-user scheduler jobs: drop any pre-10.4 global job from the persisted store,
    # then register one job per user with a cron_expr.
    purge_legacy_global_job()
    bootstrap_all_jobs()
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

# Server-side signed session cookie. SESSION_SECRET MUST be a strong random secret
# in prod; the dev default below is intentionally insecure and only keeps localhost
# working over plain HTTP. https_only is enabled in prod (HTTPS) so the cookie is
# Secure; same_site=lax + HttpOnly are always on.
#
# Prod posture is detected via SESSION_COOKIE_SECURE (already set true only in the prod
# compose). In that posture we FAIL FAST if SESSION_SECRET is missing or still the dev
# default: the session cookie is *signed, not encrypted* (Starlette + itsdangerous), so a
# publicly-known signing key lets anyone forge a {"user_id": N} cookie and impersonate any
# user. In dev posture the insecure default is allowed so local HTTP keeps working.
DEV_SESSION_SECRET = "insecure-dev-secret-change-me"
_prod_posture = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
_session_secret = os.getenv("SESSION_SECRET", "") or ""
if _prod_posture and (not _session_secret or _session_secret == DEV_SESSION_SECRET):
    raise RuntimeError(
        "SESSION_SECRET must be set to a strong random value in production "
        "(e.g. `openssl rand -hex 32`)"
    )
if not _session_secret:
    _session_secret = DEV_SESSION_SECRET

app.add_middleware(
    SessionMiddleware,
    secret_key=_session_secret,
    session_cookie="session",
    # same_site MUST be "lax", NOT "strict": the OAuth callback (GET /api/v1/auth/callback)
    # is a top-level navigation back from accounts.spotify.com. "lax" sends the session
    # cookie on that top-level GET so routers/auth.py can read request.session["oauth_state"]
    # for the CSRF check; "strict" would withhold it and every login would hit auth_error.
    same_site="lax",
    # https_only sets the cookie's Secure *attribute* — it does NOT inspect the request
    # scheme. Behind Caddy (TLS terminated, backend sees plain HTTP) the Secure flag is
    # still emitted correctly, so no ProxyHeadersMiddleware is needed for the cookie.
    https_only=_prod_posture,
    # Explicit session lifetime (14 days). This matches Starlette's silent default but is
    # now intentional and visible. Spotify tokens refresh server-side regardless (the
    # refresh token lives in User.token_json), so this only controls re-login frequency.
    max_age=1_209_600,
)

# Auth gate: business routers require a valid session (401 otherwise). auth_router
# and GET /health stay public so login (10.2) can run.
auth_gate = [Depends(get_current_user)]
app.include_router(config_router, prefix="/api/v1", dependencies=auth_gate)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(playlists_router, prefix="/api/v1", dependencies=auth_gate)
app.include_router(sync_router, prefix="/api/v1", dependencies=auth_gate)
app.include_router(blacklist_router, prefix="/api/v1", dependencies=auth_gate)
app.include_router(recently_added_router, prefix="/api/v1", dependencies=auth_gate)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
