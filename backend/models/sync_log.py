from typing import Optional
from sqlmodel import Field, SQLModel


class SyncLog(SQLModel, table=True):
    __tablename__ = "sync_log"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    status: str  # "success" or "failure"
    track_count: Optional[int] = None
    error_message: Optional[str] = None
    timestamp: str  # ISO 8601 string
