import json
import os
import secrets
from datetime import datetime

from spotipy import Spotify, SpotifyException, SpotifyOAuth
from spotipy.cache_handler import MemoryCacheHandler
from sqlmodel import Session, select

from database import engine
from migrations import run_migrations
from models.user import User
from services import blacklist_service
from services.token_manager import SQLiteCacheHandler

SCOPES = "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private user-read-private user-library-read"

LIKED_SONGS_ID = "liked_songs"
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/api/v1/auth/callback")


def _get_spotify_oauth(user: User) -> SpotifyOAuth:
    """Build a SpotifyOAuth for an existing user, keyed to their own token cache."""
    if user is None or not user.client_id:
        raise ValueError("Spotify credentials not configured — run setup first")
    return SpotifyOAuth(
        client_id=user.client_id,
        client_secret=user.client_secret,
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
        cache_handler=SQLiteCacheHandler(user.id),
    )


def start_login(request_session, client_id: str, client_secret: str) -> str:
    """Begin the per-user OAuth round-trip for an anonymous visitor.

    The visitor has no User row yet, so we hold their just-entered credentials and a
    CSRF `state` in the (anonymous) session and build a transient SpotifyOAuth backed
    by a MemoryCacheHandler (no DB write before the user exists). Returns the authorize
    URL (which embeds `state`).
    """
    state = secrets.token_urlsafe(32)
    request_session["pending_client_id"] = client_id
    request_session["pending_client_secret"] = client_secret
    request_session["oauth_state"] = state
    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
        state=state,
        cache_handler=MemoryCacheHandler(),
    )
    return sp_oauth.get_authorize_url()


def complete_login(request_session, code: str) -> None:
    """Finish the OAuth round-trip: exchange code, resolve-or-create the User, open session.

    Rebuilds the transient OAuth from the session's pending creds, exchanges the code,
    reads identity via sp.me(), resolves/creates the User by spotify_user_id, persists
    creds + token directly on the row, then opens the session and clears the transients.
    """
    client_id = request_session.get("pending_client_id")
    client_secret = request_session.get("pending_client_secret")
    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
        cache_handler=MemoryCacheHandler(),
    )
    token_info = sp_oauth.get_access_token(code, check_cache=False)
    me = Spotify(auth=token_info["access_token"]).me()
    spotify_user_id = me["id"]
    display_name = me.get("display_name")

    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.spotify_user_id == spotify_user_id)
        ).first()
        is_new_user = user is None
        if is_new_user:
            user = User(
                spotify_user_id=spotify_user_id,
                created_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            session.add(user)
        user.client_id = client_id
        user.client_secret = client_secret
        user.token_json = json.dumps(token_info)
        user.display_name = display_name
        session.commit()
        session.refresh(user)
        user_id = user.id

    # The startup migration DEFERS reshaping legacy single-tenant tables (notably
    # track_blacklist, whose user_id is part of a NOT NULL composite PK) when no User
    # exists yet to own the rows. The first login is exactly the moment an owner appears,
    # so finish the migration now instead of stranding the legacy shape until the next
    # reboot. run_migrations is idempotent, so gate it on first-user creation to avoid
    # re-running on every subsequent login.
    if is_new_user:
        run_migrations(engine)

    request_session["user_id"] = user_id
    request_session.pop("pending_client_id", None)
    request_session.pop("pending_client_secret", None)
    request_session.pop("oauth_state", None)


def get_auth_status(user: User) -> dict:
    """Per-user auth status for the session's resolved User."""
    try:
        sp_oauth = _get_spotify_oauth(user)
    except ValueError:
        return {
            "authenticated": False,
            "has_previous_auth": False,
            "spotify_user_id": None,
            "display_name": getattr(user, "display_name", None),
        }

    try:
        token_info = sp_oauth.get_cached_token()
        if token_info is None:
            return {
                "authenticated": False,
                "has_previous_auth": False,
                "spotify_user_id": None,
                "display_name": user.display_name,
            }
        token_info = sp_oauth.validate_token(token_info)
        if token_info is None:
            return {
                "authenticated": False,
                "has_previous_auth": True,
                "spotify_user_id": None,
                "display_name": user.display_name,
            }
        sp = Spotify(auth=token_info["access_token"])
        me = sp.me()
        return {
            "authenticated": True,
            "has_previous_auth": True,
            "spotify_user_id": me["id"],
            "display_name": me.get("display_name") or user.display_name,
        }
    except Exception:
        return {
            "authenticated": False,
            "has_previous_auth": True,
            "spotify_user_id": None,
            "display_name": user.display_name,
        }


def get_authenticated_client(user: User) -> Spotify:
    """Return an authenticated Spotify client for the given user, refreshing if needed."""
    sp_oauth = _get_spotify_oauth(user)
    token_info = sp_oauth.get_cached_token()
    if token_info is None:
        raise ValueError("Not authenticated — run OAuth2 flow first")
    token_info = sp_oauth.validate_token(token_info)
    if token_info is None:
        raise ValueError("Token expired and could not be refreshed")
    return Spotify(auth=token_info["access_token"])


def get_user_playlists(user: User = None) -> list[dict]:
    """Fetch all user-owned playlists + Liked Songs.

    Returns [{spotify_id, name, image_url, track_count}].
    """
    sp = get_authenticated_client(user)
    user_id = sp.me()["id"]
    dynamic_playlist_id = user.target_playlist_id

    liked_total = sp.current_user_saved_tracks(limit=1)["total"]
    results = [
        {
            "spotify_id": LIKED_SONGS_ID,
            "name": "Titres likés",
            "image_url": None,
            "track_count": liked_total,
        }
    ]
    offset = 0
    limit = 50
    while True:
        page = sp.current_user_playlists(limit=limit, offset=offset)
        for item in page["items"]:
            if not item:
                continue
            owner = item.get("owner") or {}
            if owner.get("id") == user_id and item.get("id") != dynamic_playlist_id:
                images = item.get("images") or []
                image_url = images[0]["url"] if images else None
                tracks = item.get("tracks") or item.get("items") or {}
                results.append(
                    {
                        "spotify_id": item["id"],
                        "name": item.get("name", ""),
                        "image_url": image_url,
                        "track_count": tracks.get("total", 0),
                    }
                )
        if page["next"] is None:
            break
        offset += limit
    return results


DYNAMIC_PLAYLIST_NAME = "Recent Adds"
DYNAMIC_PLAYLIST_DESCRIPTION = "Managed by playlist_spotify"


def _persist_dynamic_playlist_id(playlist_id: str, user: User) -> None:
    with Session(engine) as session:
        db_user = session.get(User, user.id)
        if db_user and db_user.target_playlist_id != playlist_id:
            db_user.target_playlist_id = playlist_id
            session.add(db_user)
            session.commit()


def _find_existing_dynamic_playlist(sp: Spotify) -> str | None:
    """Search the user's playlists for a previously-created 'Recent Adds' managed by us."""
    user_id = sp.me()["id"]
    offset = 0
    limit = 50
    while True:
        page = sp.current_user_playlists(limit=limit, offset=offset)
        for item in page["items"]:
            if not item:
                continue
            owner = item.get("owner") or {}
            if owner.get("id") != user_id:
                continue
            if item.get("name") == DYNAMIC_PLAYLIST_NAME and (
                item.get("description") == DYNAMIC_PLAYLIST_DESCRIPTION
            ):
                return item["id"]
        if page["next"] is None:
            return None
        offset += limit


def get_or_create_dynamic_playlist(sp: Spotify, user: User) -> str:
    """Return the Spotify ID of the user's 'Recent Adds' playlist, creating it if needed.

    Self-heals when user.target_playlist_id is missing but the playlist already exists
    on Spotify (e.g. legacy installs where the create succeeded but the write didn't
    commit) — searches by name + managed description and re-adopts it. The id is stored
    per-user on user.target_playlist_id.
    """
    stored_id = user.target_playlist_id

    if stored_id:
        try:
            sp.playlist(stored_id, fields="id")
            return stored_id
        except Exception:
            pass  # Playlist deleted on Spotify — fall through

    # Re-adopt an existing managed playlist before creating a duplicate
    existing_id = _find_existing_dynamic_playlist(sp)
    if existing_id:
        _persist_dynamic_playlist_id(existing_id, user)
        return existing_id

    new_playlist = sp.current_user_playlist_create(
        DYNAMIC_PLAYLIST_NAME, public=False, description=DYNAMIC_PLAYLIST_DESCRIPTION
    )
    new_id = new_playlist["id"]
    _persist_dynamic_playlist_id(new_id, user)
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


def get_playlist_tracks(
    playlist_id: str, sp: Spotify = None, since: str | None = None, user: User = None
) -> list[dict]:
    """
    Fetch tracks from a playlist (or Liked Songs).

    When `since` is provided, only returns tracks with added_at > since.
    For regular playlists (insertion-ordered oldest-first), reverse-paginates from
    the end and stops as soon as a page contains any track at or before `since`.
    """
    if sp is None:
        sp = get_authenticated_client(user)
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


def _build_track_row(track: dict, added_at: str, blacklisted_ids: set[str]) -> dict:
    album = track.get("album") or {}
    images = album.get("images") or []
    artists = [a.get("name") for a in (track.get("artists") or []) if a.get("name")]
    return {
        "spotify_id": track["id"],
        "title": track.get("name", ""),
        "artists": artists,
        "album": album.get("name", ""),
        "image_url": images[0]["url"] if images else None,
        "added_at": added_at or "",
        "duration_ms": int(track.get("duration_ms") or 0),
        "explicit": bool(track.get("explicit", False)),
        "has_video": bool(track.get("is_video", False)),
        "is_blacklisted": track["id"] in blacklisted_ids,
    }


def get_playlist_tracks_full(playlist_id: str, user: User = None) -> list[dict]:
    """Return every track of a playlist (or Liked Songs) as full rich-shape dicts.

    Mirrors get_recently_added_tracks shape. For LIKED_SONGS_ID, uses the
    saved-tracks API. Re-raises SpotifyException on 404 (router translates to
    HTTP 404) and on other Spotify errors (router → 502).
    """
    sp = get_authenticated_client(user)
    with Session(engine) as session:
        blacklisted_ids = blacklist_service.get_blacklisted_ids(session, user.id)
    results: list[dict] = []
    offset = 0

    if playlist_id == LIKED_SONGS_ID:
        limit = 50
        while True:
            page = sp.current_user_saved_tracks(limit=limit, offset=offset)
            for item in page["items"]:
                if item is None:
                    continue
                track = item.get("track")
                if not track or not track.get("id") or track.get("is_local"):
                    continue
                results.append(_build_track_row(track, item.get("added_at") or "", blacklisted_ids))
            if page.get("next") is None:
                break
            offset += limit
        return results

    # Existence probe — let SpotifyException propagate (router handles 404 vs 502)
    sp.playlist(playlist_id, fields="id")

    limit = 100
    while True:
        page = sp.playlist_items(
            playlist_id,
            limit=limit,
            offset=offset,
            fields=(
                "items(added_at,is_local,"
                "track(id,name,duration_ms,explicit,is_local,is_video,"
                "artists(name),album(name,images)),"
                "item(id,name,duration_ms,explicit,is_local,is_video,"
                "artists(name),album(name,images))),next"
            ),
        )
        for item in page["items"]:
            if item is None or item.get("is_local"):
                continue
            track = item.get("track") or item.get("item")
            if not track or not track.get("id") or track.get("is_local"):
                continue
            results.append(_build_track_row(track, item.get("added_at") or "", blacklisted_ids))
        if page.get("next") is None:
            break
        offset += limit
    return results


def get_playlist_tracks_page(
    playlist_id: str, limit: int, offset: int, user: User = None
) -> dict:
    """Return a single page of tracks plus pagination metadata.

    next_offset advances by raw page length (Spotify's notion of progress), not
    by kept length (post-filter). Returns next_offset=None when end reached.
    """
    sp = get_authenticated_client(user)
    with Session(engine) as session:
        blacklisted_ids = blacklist_service.get_blacklisted_ids(session, user.id)

    items: list[dict] = []

    if playlist_id == LIKED_SONGS_ID:
        page = sp.current_user_saved_tracks(limit=limit, offset=offset)
        total = int(page.get("total") or 0)
        raw = page.get("items") or []
        for item in raw:
            if item is None:
                continue
            track = item.get("track")
            if not track or not track.get("id") or track.get("is_local"):
                continue
            items.append(
                _build_track_row(track, item.get("added_at") or "", blacklisted_ids)
            )
        next_offset = offset + len(raw) if (offset + len(raw)) < total else None
        return {"items": items, "next_offset": next_offset, "total": total}

    # Existence probe — let SpotifyException propagate (router handles 404 vs 502)
    sp.playlist(playlist_id, fields="tracks(total)")

    page = sp.playlist_items(
        playlist_id,
        limit=limit,
        offset=offset,
        fields=(
            "total,items(added_at,is_local,"
            "track(id,name,duration_ms,explicit,is_local,is_video,"
            "artists(name),album(name,images)),"
            "item(id,name,duration_ms,explicit,is_local,is_video,"
            "artists(name),album(name,images))),next"
        ),
    )
    total = int(page.get("total") or 0)
    raw = page.get("items") or []
    for item in raw:
        if item is None or item.get("is_local"):
            continue
        track = item.get("track") or item.get("item")
        if not track or not track.get("id") or track.get("is_local"):
            continue
        items.append(
            _build_track_row(track, item.get("added_at") or "", blacklisted_ids)
        )
    next_offset = offset + len(raw) if (offset + len(raw)) < total else None
    return {"items": items, "next_offset": next_offset, "total": total}


def get_recently_added_tracks(user: User = None) -> list[dict]:
    """Return the current contents of the dynamic playlist as shaped dicts.

    Returns [] when the dynamic playlist has not been created yet (fresh install)
    or has been deleted from Spotify. Re-raises ValueError if not authenticated
    and SpotifyException for non-404 Spotify errors.
    """
    playlist_id = user.target_playlist_id
    with Session(engine) as session:
        blacklisted_ids = blacklist_service.get_blacklisted_ids(session, user.id)
    if not playlist_id:
        return []

    sp = get_authenticated_client(user)
    try:
        sp.playlist(playlist_id, fields="id")
    except SpotifyException as exc:
        if exc.http_status == 404:
            return []
        raise

    results: list[dict] = []
    offset = 0
    limit = 100
    while True:
        page = sp.playlist_items(
            playlist_id,
            limit=limit,
            offset=offset,
            fields=(
                "items(added_at,is_local,"
                "track(id,name,duration_ms,explicit,is_local,is_video,"
                "artists(name),album(name,images)),"
                "item(id,name,duration_ms,explicit,is_local,is_video,"
                "artists(name),album(name,images))),next"
            ),
        )
        for item in page["items"]:
            if item is None or item.get("is_local"):
                continue
            track = item.get("track") or item.get("item")
            if not track or not track.get("id") or track.get("is_local"):
                continue
            album = track.get("album") or {}
            images = album.get("images") or []
            artists = [a.get("name") for a in (track.get("artists") or []) if a.get("name")]
            results.append({
                "spotify_id": track["id"],
                "title": track.get("name", ""),
                "artists": artists,
                "album": album.get("name", ""),
                "image_url": images[0]["url"] if images else None,
                "added_at": item.get("added_at") or "",
                "duration_ms": int(track.get("duration_ms") or 0),
                "explicit": bool(track.get("explicit", False)),
                # Spotify rarely flags `is_video` on normal tracks; default False.
                "has_video": bool(track.get("is_video", False)),
                "is_blacklisted": track["id"] in blacklisted_ids,
            })
        if page.get("next") is None:
            break
        offset += limit
    return results
