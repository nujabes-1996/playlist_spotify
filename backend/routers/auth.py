import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from services import spotify as spotify_service

router = APIRouter(tags=["auth"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


class ConnectResponse(BaseModel):
    auth_url: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    spotify_user_id: Optional[str] = None


@router.post("/auth/connect", response_model=ConnectResponse)
def connect_spotify() -> ConnectResponse:
    try:
        auth_url = spotify_service.get_auth_url()
        return ConnectResponse(auth_url=auth_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/auth/callback")
def spotify_callback(code: Optional[str] = None, error: Optional[str] = None):
    if error or code is None:
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_error=1")
    try:
        spotify_service.handle_callback(code)
        return RedirectResponse(url=FRONTEND_URL)
    except Exception:
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_error=1")


@router.get("/auth/status", response_model=AuthStatusResponse)
def auth_status() -> AuthStatusResponse:
    status = spotify_service.get_auth_status()
    return AuthStatusResponse(**status)
