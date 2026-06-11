"""One-shot idempotent startup migration for Story 10.3 (multi-tenant data scoping).

`SQLModel.metadata.create_all()` only CREATES missing tables — it never alters an
existing table's columns or constraints (AR8: no Alembic). This module reshapes the
legacy single-tenant tables (`playlist`, `track_blacklist`, `sync_log`) to carry a
`user_id` owner, backfills existing rows to the owner `User`, and copies the legacy
global `config` settings onto that owner.

It is idempotent — safe to run on every boot — and a no-op on a fresh install (where
`create_all` already produced the correct multi-tenant schema, so every "column
missing?" guard is false and there is no legacy `config`/data to migrate).

Call it AFTER `SQLModel.metadata.create_all(engine)` so the `user` table exists and
any fresh tables are already correctly shaped.

NOTE on the reshape mechanism: `playlist.spotify_id` and `track_blacklist.spotify_id`
were declared with `unique=True`/`primary_key`, so SQLite backs them with an autoindex
tied to a UNIQUE/PK constraint that `DROP INDEX` cannot remove. Changing those
constraints therefore requires a full table rebuild (rename → recreate from the model →
INSERT…SELECT → drop), not an index swap. `sync_log` only gains a nullable column, so a
plain `ADD COLUMN` suffices there.
"""
from sqlalchemy import text
from sqlmodel import Session, select

from models.playlist import Playlist
from models.track_blacklist import TrackBlacklist
from models.user import User


def _table_exists(conn, table: str) -> bool:
    return (
        conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
            {"n": table},
        ).first()
        is not None
    )


def _columns(conn, table: str) -> set[str]:
    # PRAGMA does not accept bound params; table names here are hardcoded constants.
    rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def _resolve_owner_id(engine) -> int | None:
    """The single/first User row (used to backfill legacy rows with an owner id)."""
    with Session(engine) as session:
        user = session.exec(select(User)).first()
        return user.id if user else None


def _migrate_user(conn) -> None:
    """Add the 10.3 `last_sync_at` column to a pre-existing `user` table.

    10.1 created `user` with playlist_size/cron_expr/target_playlist_id but NOT
    last_sync_at, and `create_all` never alters an existing table. A nullable
    ADD COLUMN needs no owner and is a no-op once the column exists.
    """
    if not _table_exists(conn, "user"):
        return
    if "last_sync_at" not in _columns(conn, "user"):
        conn.exec_driver_sql("ALTER TABLE user ADD COLUMN last_sync_at VARCHAR")


def _migrate_playlist(conn, owner_id: int | None) -> None:
    if not _table_exists(conn, "playlist"):
        return
    if "user_id" not in _columns(conn, "playlist"):
        # Legacy global-unique shape → rebuild to composite unique (user_id, spotify_id)
        # with a nullable user_id. user_id is nullable, so this is safe even with no owner.
        conn.exec_driver_sql("ALTER TABLE playlist RENAME TO _playlist_legacy")
        Playlist.__table__.create(conn)
        conn.execute(
            text(
                "INSERT INTO playlist (id, user_id, spotify_id, name, is_included, is_hidden) "
                "SELECT id, :owner, spotify_id, name, is_included, is_hidden FROM _playlist_legacy"
            ),
            {"owner": owner_id},
        )
        conn.exec_driver_sql("DROP TABLE _playlist_legacy")
    elif owner_id is not None:
        # Backfill legacy `user_id IS NULL` rows to the owner. A partially-migrated DB can
        # ALREADY hold an owned row for the same spotify_id — e.g. the first boot created
        # NULL-owner rows (no user existed yet), then a per-user re-sync inserted owned rows
        # before this backfill ever ran. A blind `UPDATE ... WHERE user_id IS NULL` would
        # then violate the (user_id, spotify_id) UNIQUE constraint. So collapse each
        # colliding pair first: the legacy NULL row carries the authoritative curation
        # (is_included/is_hidden) while the re-synced owned row holds defaults, so copy the
        # curation onto the owned row, then drop the NULL duplicate. Whatever NULL rows have
        # no owned twin are simply reassigned by the final UPDATE.
        conn.execute(
            text(
                "UPDATE playlist SET "
                "  is_included = (SELECT l.is_included FROM playlist l "
                "                 WHERE l.spotify_id = playlist.spotify_id AND l.user_id IS NULL), "
                "  is_hidden   = (SELECT l.is_hidden   FROM playlist l "
                "                 WHERE l.spotify_id = playlist.spotify_id AND l.user_id IS NULL) "
                "WHERE user_id = :owner AND EXISTS "
                "  (SELECT 1 FROM playlist l "
                "   WHERE l.spotify_id = playlist.spotify_id AND l.user_id IS NULL)"
            ),
            {"owner": owner_id},
        )
        conn.execute(
            text(
                "DELETE FROM playlist WHERE user_id IS NULL AND EXISTS "
                "  (SELECT 1 FROM playlist o "
                "   WHERE o.spotify_id = playlist.spotify_id AND o.user_id = :owner)"
            ),
            {"owner": owner_id},
        )
        conn.execute(
            text("UPDATE playlist SET user_id = :owner WHERE user_id IS NULL"),
            {"owner": owner_id},
        )


def _migrate_sync_log(conn, owner_id: int | None) -> None:
    if not _table_exists(conn, "sync_log"):
        return
    if "user_id" not in _columns(conn, "sync_log"):
        conn.exec_driver_sql("ALTER TABLE sync_log ADD COLUMN user_id INTEGER")
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_sync_log_user_id ON sync_log (user_id)"
        )
    if owner_id is not None:
        conn.execute(
            text("UPDATE sync_log SET user_id = :owner WHERE user_id IS NULL"),
            {"owner": owner_id},
        )


def _migrate_track_blacklist(conn, owner_id: int | None) -> None:
    if not _table_exists(conn, "track_blacklist"):
        return
    if "user_id" in _columns(conn, "track_blacklist"):
        return  # already composite-PK shape
    # Legacy single-column-PK shape → rebuild to composite PK (spotify_id, user_id).
    # user_id is part of the PK (NOT NULL), so legacy rows need an owner to assign.
    count = conn.exec_driver_sql("SELECT COUNT(*) FROM track_blacklist").scalar()
    if count and owner_id is None:
        # Cannot assign legacy blacklist rows to a NOT NULL owner yet (no user has
        # logged in). Defer: this migration is idempotent and completes on a later
        # boot once the owner exists. Leaving the legacy shape is safe because the
        # auth gate blocks every blacklist query until a user exists.
        return
    conn.exec_driver_sql(
        "ALTER TABLE track_blacklist RENAME TO _track_blacklist_legacy"
    )
    TrackBlacklist.__table__.create(conn)
    conn.execute(
        text(
            "INSERT INTO track_blacklist (spotify_id, user_id, blacklisted_at) "
            "SELECT spotify_id, :owner, blacklisted_at FROM _track_blacklist_legacy"
        ),
        {"owner": owner_id},
    )
    conn.exec_driver_sql("DROP TABLE _track_blacklist_legacy")


def _migrate_settings(engine, owner_id: int) -> None:
    """Copy the legacy global `config` settings onto the owner User (read via raw SQL).

    Idempotent: only fills owner fields still at their default/None, so a re-run — or a
    user who edited their settings after the first migration — is never clobbered.
    """
    with engine.connect() as conn:
        if not _table_exists(conn, "config"):
            return
        row = conn.execute(
            text(
                "SELECT playlist_size, cron_expr, dynamic_playlist_id, last_sync_at "
                "FROM config LIMIT 1"
            )
        ).first()
    if row is None:
        return
    playlist_size, cron_expr, dynamic_playlist_id, last_sync_at = row
    with Session(engine) as session:
        owner = session.get(User, owner_id)
        if owner is None:
            return
        if owner.cron_expr is None and cron_expr:
            owner.cron_expr = cron_expr
        if owner.target_playlist_id is None and dynamic_playlist_id:
            owner.target_playlist_id = dynamic_playlist_id
        if owner.last_sync_at is None and last_sync_at:
            owner.last_sync_at = last_sync_at
        if owner.playlist_size == 50 and playlist_size is not None:
            owner.playlist_size = playlist_size
        session.add(owner)
        session.commit()


def run_migrations(engine) -> None:
    """Reshape legacy tables, backfill rows to the owner, copy Config settings onto it."""
    # Add user.last_sync_at FIRST: _resolve_owner_id issues `SELECT user.*`, which
    # would fail on a legacy `user` table that predates the 10.3 column.
    with engine.begin() as conn:
        _migrate_user(conn)
    owner_id = _resolve_owner_id(engine)
    with engine.begin() as conn:
        _migrate_playlist(conn, owner_id)
        _migrate_sync_log(conn, owner_id)
        _migrate_track_blacklist(conn, owner_id)
    if owner_id is not None:
        _migrate_settings(engine, owner_id)
