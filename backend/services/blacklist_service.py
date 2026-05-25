from sqlmodel import Session, select

from models.track_blacklist import TrackBlacklist


def get_blacklisted_ids(session: Session) -> set[str]:
    """Return the current set of blacklisted spotify_ids.

    Caller owns the Session — do NOT open a new one here.
    Sync engine consumes this once per run_sync() invocation.
    """
    rows = session.exec(select(TrackBlacklist)).all()
    return {row.spotify_id for row in rows}
