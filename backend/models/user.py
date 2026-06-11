from typing import Optional
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    spotify_user_id: str = Field(unique=True)
    display_name: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token_json: Optional[str] = None
    playlist_size: int = Field(default=50)
    cron_expr: Optional[str] = None
    target_playlist_id: Optional[str] = None
    last_sync_at: Optional[str] = None
    created_at: Optional[str] = None
