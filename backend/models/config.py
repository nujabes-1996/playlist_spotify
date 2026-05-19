from typing import Optional
from sqlmodel import Field, SQLModel


class Config(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    playlist_size: int = Field(default=50)
    cron_expr: Optional[str] = None
    spotify_token_json: Optional[str] = None
