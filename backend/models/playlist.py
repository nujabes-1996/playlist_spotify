from typing import Optional
from sqlmodel import Field, SQLModel


class Playlist(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    spotify_id: str = Field(unique=True)
    name: str
    is_included: bool = Field(default=False)
