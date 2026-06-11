from sqlmodel import Session, select

from models.track_blacklist import TrackBlacklist


def get_blacklisted_ids(session: Session, user_id: int) -> set[str]:
    """Return the given user's set of blacklisted spotify_ids.

    Caller owns the Session — do NOT open a new one here.
    Sync engine consumes this once per run_sync() invocation.
    """
    rows = session.exec(
        select(TrackBlacklist).where(TrackBlacklist.user_id == user_id)
    ).all()
    return {row.spotify_id for row in rows}
