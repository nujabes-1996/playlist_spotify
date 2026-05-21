from sqlmodel import Field, SQLModel


class TrackBlacklist(SQLModel, table=True):
    __tablename__ = "track_blacklist"  # type: ignore[assignment]

    spotify_id: str = Field(primary_key=True)
    blacklisted_at: str
