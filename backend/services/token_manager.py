import json
from spotipy.cache_handler import CacheHandler
from sqlmodel import Session, select

from database import engine
from models.config import Config


class SQLiteCacheHandler(CacheHandler):
    """Stores spotipy OAuth token in the SQLite config table.

    Replaces default CacheFileHandler (filesystem-based, not Docker-safe).
    """

    def get_cached_token(self):
        with Session(engine) as session:
            config = session.exec(select(Config)).first()
            if config and config.spotify_token_json:
                return json.loads(config.spotify_token_json)
            return None

    def save_token_to_cache(self, token_info):
        with Session(engine) as session:
            config = session.exec(select(Config)).first()
            if config is None:
                config = Config()
                session.add(config)
            config.spotify_token_json = json.dumps(token_info)
            session.commit()
