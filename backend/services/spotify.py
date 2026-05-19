import os

from spotipy import Spotify, SpotifyOAuth
from sqlmodel import Session, select

from database import engine
from models.config import Config
from services.token_manager import SQLiteCacheHandler

SCOPES = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private user-read-private"
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/api/v1/auth/callback")


def _get_spotify_oauth() -> SpotifyOAuth:
    with Session(engine) as session:
        config = session.exec(select(Config)).first()
        if config is None or not config.client_id:
            raise ValueError("Spotify credentials not configured — run setup first")
        client_id = config.client_id
        client_secret = config.client_secret
    return SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
        cache_handler=SQLiteCacheHandler(),
    )


def get_auth_url() -> str:
    sp_oauth = _get_spotify_oauth()
    return sp_oauth.get_authorize_url()


def handle_callback(code: str) -> None:
    sp_oauth = _get_spotify_oauth()
    sp_oauth.get_access_token(code, check_cache=False)


def get_auth_status() -> dict:
    try:
        sp_oauth = _get_spotify_oauth()
        token_info = sp_oauth.get_cached_token()
        if token_info is None:
            return {"authenticated": False, "spotify_user_id": None}
        token_info = sp_oauth.validate_token(token_info)
        if token_info is None:
            return {"authenticated": False, "spotify_user_id": None}
        sp = Spotify(auth=token_info["access_token"])
        user = sp.me()
        return {"authenticated": True, "spotify_user_id": user["id"]}
    except Exception:
        return {"authenticated": False, "spotify_user_id": None}
