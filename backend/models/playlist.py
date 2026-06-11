from typing import Optional
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Playlist(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("user_id", "spotify_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    spotify_id: str
    name: str
    is_included: bool = Field(default=False)
    is_hidden: bool = Field(default=False, sa_column_kwargs={"server_default": "0"})
