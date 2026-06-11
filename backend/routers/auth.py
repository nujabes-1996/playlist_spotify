import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from dependencies import SessionDep
from models.user import User
from services import spotify as spotify_service

router = APIRouter(tags=["auth"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


class ConnectRequest(BaseModel):
    client_id: str
    client_secret: str


class ConnectResponse(BaseModel):
    auth_url: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    has_previous_auth: bool = False
    spotify_user_id: Optional[str] = None
    display_name: Optional[str] = None
    # Public, non-secret callback URL the backend passes to SpotifyOAuth. The login screen
    # renders this so users register the exact URI the backend will send to Spotify (in prod
    # https://<DOMAIN>/api/v1/auth/callback) instead of a hardcoded dev string.
    redirect_uri: str = ""


@router.post("/auth/connect", response_model=ConnectResponse)
def connect_spotify(payload: ConnectRequest, request: Request) -> ConnectResponse:
    """Public: start the per-user OAuth round-trip with the visitor's own credentials."""
    try:
        auth_url = spotify_service.start_login(
            request.session, payload.client_id, payload.client_secret
        )
        return ConnectResponse(auth_url=auth_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/auth/callback")
def spotify_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    """Public: validate CSRF state, exchange the code, resolve-or-create the user, open session."""
    if error or code is None or state != request.session.get("oauth_state"):
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_error=1")
    try:
        spotify_service.complete_login(request.session, code)
        return RedirectResponse(url=FRONTEND_URL)
    except Exception:
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_error=1")


@router.post("/auth/logout")
def logout(request: Request) -> dict:
    """Public: clear the session cookie. DB rows are preserved for the next login."""
    request.session.clear()
    return {"ok": True}


@router.get("/auth/status", response_model=AuthStatusResponse)
def auth_status(request: Request, session: SessionDep) -> AuthStatusResponse:
    """Public, session-based: report auth state for the session's user (if any)."""
    # redirect_uri is public and posture-independent — include it in EVERY branch so the
    # pre-auth login screen (which renders for unauthenticated visitors) always receives it.
    redirect_uri = spotify_service.REDIRECT_URI
    user_id = request.session.get("user_id")
    if not user_id:
        return AuthStatusResponse(
            authenticated=False, has_previous_auth=False, spotify_user_id=None,
            display_name=None, redirect_uri=redirect_uri,
        )
    user = session.get(User, user_id)
    if user is None:
        return AuthStatusResponse(
            authenticated=False, has_previous_auth=False, spotify_user_id=None,
            display_name=None, redirect_uri=redirect_uri,
        )
    status = spotify_service.get_auth_status(user)
    return AuthStatusResponse(**status, redirect_uri=redirect_uri)
