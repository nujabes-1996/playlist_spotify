import json
from spotipy.cache_handler import CacheHandler
from sqlmodel import Session

from database import engine
from models.user import User


class SQLiteCacheHandler(CacheHandler):
    """Stores spotipy OAuth token on a User row in SQLite, keyed by user_id.

    Replaces default CacheFileHandler (filesystem-based, not Docker-safe) and the
    legacy global Config-based handler. Each user's token lives on User.token_json,
    so a token saved for user A is invisible to user B.
    """

    def __init__(self, user_id: int):
        self.user_id = user_id

    def get_cached_token(self):
        with Session(engine) as session:
            user = session.get(User, self.user_id)
            if user and user.token_json:
                return json.loads(user.token_json)
            return None

    def save_token_to_cache(self, token_info):
        with Session(engine) as session:
            user = session.get(User, self.user_id)
            # Defensive: the callback persists the first token directly on the row,
            # so the row always exists by the time refreshes flow through here. If
            # it's missing (e.g. user deleted), no-op rather than create a ghost row.
            if user is None:
                return
            user.token_json = json.dumps(token_info)
            session.add(user)
            session.commit()
