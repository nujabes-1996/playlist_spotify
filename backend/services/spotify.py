import os

from spotipy import Spotify, SpotifyOAuth
from sqlmodel import Session, select

from database import engine
from models.config import Config
from services.token_manager import SQLiteCacheHandler

SCOPES = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private user-read-private user-library-read"

LIKED_SONGS_ID = "liked_songs"
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
    except ValueError:
        return {"authenticated": False, "has_previous_auth": False, "spotify_user_id": None}

    try:
        token_info = sp_oauth.get_cached_token()
        if token_info is None:
            return {"authenticated": False, "has_previous_auth": False, "spotify_user_id": None}
        token_info = sp_oauth.validate_token(token_info)
        if token_info is None:
            return {"authenticated": False, "has_previous_auth": True, "spotify_user_id": None}
        sp = Spotify(auth=token_info["access_token"])
        user = sp.me()
        return {"authenticated": True, "has_previous_auth": True, "spotify_user_id": user["id"]}
    except Exception:
        return {"authenticated": False, "has_previous_auth": True, "spotify_user_id": None}


def get_authenticated_client() -> Spotify:
    """Return an authenticated Spotify client, refreshing the token if needed."""
    sp_oauth = _get_spotify_oauth()
    token_info = sp_oauth.get_cached_token()
    if token_info is None:
        raise ValueError("Not authenticated — run OAuth2 flow first")
    token_info = sp_oauth.validate_token(token_info)
    if token_info is None:
        raise ValueError("Token expired and could not be refreshed")
    return Spotify(auth=token_info["access_token"])


def get_user_playlists() -> list[dict]:
    """Fetch all user-owned playlists + Liked Songs. Returns [{spotify_id, name}]."""
    sp = get_authenticated_client()
    user_id = sp.me()["id"]

    with Session(engine) as session:
        config = session.exec(select(Config)).first()
        dynamic_playlist_id = config.dynamic_playlist_id if config else None

    results = [{"spotify_id": LIKED_SONGS_ID, "name": "Titres likés"}]
    offset = 0
    limit = 50
    while True:
        page = sp.current_user_playlists(limit=limit, offset=offset)
        for item in page["items"]:
            if item["owner"]["id"] == user_id and item["id"] != dynamic_playlist_id:
                results.append({"spotify_id": item["id"], "name": item["name"]})
        if page["next"] is None:
            break
        offset += limit
    return results


def get_or_create_dynamic_playlist(sp: Spotify) -> str:
    """Return the Spotify ID of the 'Recent Adds' playlist, creating it if needed."""
    with Session(engine) as session:
        config = session.exec(select(Config)).first()
        stored_id = config.dynamic_playlist_id if config else None

    if stored_id:
        try:
            sp.playlist(stored_id, fields="id")
            return stored_id
        except Exception:
            pass  # Playlist deleted on Spotify — fall through to create

    new_playlist = sp.current_user_playlist_create(
        "Recent Adds", public=False, description="Managed by playlist_spotify"
    )
    new_id = new_playlist["id"]

    with Session(engine) as session:
        config = session.exec(select(Config)).first()
        if config:
            config.dynamic_playlist_id = new_id
            session.add(config)
            session.commit()

    return new_id


def replace_playlist_tracks(playlist_id: str, track_uris: list[str], sp: Spotify) -> None:
    """Replace playlist contents with track_uris. Handles >100 tracks via chunking."""
    sp.playlist_replace_items(playlist_id, track_uris[:100])
    for i in range(100, len(track_uris), 100):
        sp.playlist_add_items(playlist_id, track_uris[i : i + 100])


def _get_liked_tracks(sp: Spotify, since: str | None = None) -> list[dict]:
    """Fetch saved/liked tracks, stopping early at `since` (API returns newest-first)."""
    results = []
    offset = 0
    limit = 50
    while True:
        page = sp.current_user_saved_tracks(limit=limit, offset=offset)
        done = False
        for item in page["items"]:
            track = item.get("track")
            if track and track.get("id"):
                added_at = item.get("added_at") or ""
                if since and added_at <= since:
                    done = True
                    break
                results.append({"spotify_id": track["id"], "uri": track["uri"], "added_at": added_at})
        if done or page["next"] is None:
            break
        offset += limit
    return results


def get_playlist_tracks(playlist_id: str, sp: Spotify = None, since: str | None = None) -> list[dict]:
    """
    Fetch tracks from a playlist (or Liked Songs).

    When `since` is provided, only returns tracks with added_at > since.
    For regular playlists (insertion-ordered oldest-first), reverse-paginates from
    the end and stops as soon as a page contains any track at or before `since`.
    """
    if sp is None:
        sp = get_authenticated_client()
    if playlist_id == LIKED_SONGS_ID:
        return _get_liked_tracks(sp, since=since)

    limit = 100
    results = []

    if since:
        probe = sp.playlist_items(playlist_id, limit=1, fields="total")
        total = probe.get("total", 0)
        if total == 0:
            return []
        offset = ((total - 1) // limit) * limit  # last page

        while True:
            page = sp.playlist_items(
                playlist_id,
                limit=limit,
                offset=offset,
                fields="items(item(id,uri),added_at),next",
            )
            has_old = False
            for item in page["items"]:
                track = item.get("item")
                if track and track.get("id"):
                    added_at = item.get("added_at") or ""
                    if added_at <= since:
                        has_old = True
                    else:
                        results.append({"spotify_id": track["id"], "uri": track["uri"], "added_at": added_at})
            if has_old or offset == 0:
                break
            offset = max(0, offset - limit)
        return results

    # Full fetch (no since filter)
    offset = 0
    while True:
        page = sp.playlist_items(
            playlist_id,
            limit=limit,
            offset=offset,
            fields="items(item(id,uri),added_at),next",
        )
        for item in page["items"]:
            track = item.get("item")
            if track and track.get("id"):
                results.append({
                    "spotify_id": track["id"],
                    "uri": track["uri"],
                    "added_at": item.get("added_at") or "",
                })
        if page["next"] is None:
            break
        offset += limit
    return results
