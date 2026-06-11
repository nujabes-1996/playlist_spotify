"""Tests for Story 10.3: Data Scoping Migration (multi-tenant correctness).

Proves per-user isolation across all four concerns (playlists, blacklist, sync logs,
settings), the dynamic-playlist-per-user wiring, the user-scoped get_blacklisted_ids
signature, and the one-shot idempotent legacy migration/backfill.

Router tests share one in-memory DB and flip the current user via the `current` holder
so cross-tenant leakage is exercised with two real, persisted User rows.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from dependencies import get_current_user
from migrations import run_migrations
from models.playlist import Playlist
from models.sync_log import SyncLog
from models.track_blacklist import TrackBlacklist
from models.user import User
import services.blacklist_service as blacklist_service
import services.spotify as spotify_service


@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(name="users")
def users_fixture(session):
    a = User(spotify_user_id="user_a", client_id="cid_a", client_secret="s")
    b = User(spotify_user_id="user_b", client_id="cid_b", client_secret="s")
    session.add(a)
    session.add(b)
    session.commit()
    session.refresh(a)
    session.refresh(b)
    return a, b


@pytest.fixture(name="current")
def current_fixture():
    """Mutable holder for the active user — tests reassign current['user']."""
    return {"user": None}


@pytest.fixture(name="client")
def client_fixture(session, users, current):
    current["user"] = users[0]
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: current["user"]
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ────────────────────────────────────────────────────────────
# AC#2/#5/#6 (a)(b) — Playlist isolation + per-user uniqueness
# ────────────────────────────────────────────────────────────


def test_two_users_same_spotify_id_no_collision_and_scoped(client, current, users):
    a, b = users
    shared = [{"spotify_id": "shared", "name": "Shared", "image_url": None, "track_count": 1}]
    with patch(
        "routers.playlists.spotify_service.get_user_playlists", return_value=shared
    ):
        current["user"] = a
        ra = client.get("/api/v1/playlists")
        current["user"] = b
        rb = client.get("/api/v1/playlists")

    assert ra.status_code == 200 and rb.status_code == 200
    # Both users own a 'shared' playlist row without unique collision...
    assert [p["spotify_id"] for p in ra.json()] == ["shared"]
    assert [p["spotify_id"] for p in rb.json()] == ["shared"]


def test_patch_playlist_owned_by_other_user_returns_404(client, current, session, users):
    a, b = users
    # A row that belongs only to user B.
    session.add(Playlist(user_id=b.id, spotify_id="only_b", name="B's"))
    session.commit()

    current["user"] = a
    r = client.patch("/api/v1/playlists/only_b", json={"is_included": True})
    assert r.status_code == 404

    # B can mutate their own row.
    current["user"] = b
    r = client.patch("/api/v1/playlists/only_b", json={"is_included": True})
    assert r.status_code == 200
    assert r.json()["is_included"] is True


def test_get_playlists_prune_is_user_scoped(client, current, session, users):
    """Pruning rows no longer on Spotify must not touch the other user's rows."""
    a, b = users
    session.add(Playlist(user_id=b.id, spotify_id="b_keeps", name="B keeps"))
    session.commit()

    with patch(
        "routers.playlists.spotify_service.get_user_playlists",
        return_value=[{"spotify_id": "a_only", "name": "A", "image_url": None, "track_count": 0}],
    ):
        current["user"] = a
        client.get("/api/v1/playlists")  # A's sync prunes A's stale rows only

    # B's row survives A's prune.
    assert session.exec(
        select(Playlist).where(Playlist.user_id == b.id, Playlist.spotify_id == "b_keeps")
    ).first() is not None


# ────────────────────────────────────────────────────────────
# AC#2/#5/#6 (c) — Blacklist isolation + composite PK
# ────────────────────────────────────────────────────────────


def test_two_users_blacklist_same_track_coexist_and_scoped(client, current, users):
    a, b = users
    current["user"] = a
    assert client.post("/api/v1/blacklist", json={"spotify_id": "track1"}).status_code == 201
    current["user"] = b
    assert client.post("/api/v1/blacklist", json={"spotify_id": "track1"}).status_code == 201

    # Each only sees their own row.
    current["user"] = a
    assert [r["spotify_id"] for r in client.get("/api/v1/blacklist").json()] == ["track1"]
    current["user"] = b
    assert [r["spotify_id"] for r in client.get("/api/v1/blacklist").json()] == ["track1"]


def test_delete_blacklist_is_user_scoped(client, current, users):
    a, b = users
    current["user"] = a
    client.post("/api/v1/blacklist", json={"spotify_id": "t"})
    current["user"] = b
    client.post("/api/v1/blacklist", json={"spotify_id": "t"})

    # A deletes their own row; B's must remain.
    current["user"] = a
    assert client.delete("/api/v1/blacklist/t").status_code == 204
    assert client.get("/api/v1/blacklist").json() == []
    current["user"] = b
    assert [r["spotify_id"] for r in client.get("/api/v1/blacklist").json()] == ["t"]


# ────────────────────────────────────────────────────────────
# AC#5 (d) — Sync logs / status per-user
# ────────────────────────────────────────────────────────────


def test_sync_logs_and_status_are_user_scoped(client, current, session, users):
    a, b = users
    session.add(SyncLog(user_id=a.id, status="success", track_count=5, timestamp="2026-05-01T10:00:00Z"))
    session.add(SyncLog(user_id=b.id, status="failure", error_message="b", timestamp="2026-05-02T10:00:00Z"))
    session.commit()

    current["user"] = a
    logs = client.get("/api/v1/sync/logs").json()
    assert [l["status"] for l in logs] == ["success"]
    assert client.get("/api/v1/sync/status").json()["status"] == "success"

    current["user"] = b
    logs = client.get("/api/v1/sync/logs").json()
    assert [l["status"] for l in logs] == ["failure"]


# ────────────────────────────────────────────────────────────
# AC#3/#9 (e) — Settings on User, per-user
# ────────────────────────────────────────────────────────────


def test_patch_config_is_per_user(client, current, users, session):
    a, b = users
    current["user"] = a
    r = client.patch("/api/v1/config", json={"playlist_size": 100})
    assert r.status_code == 200 and r.json()["playlist_size"] == 100

    # B is untouched (still default 50).
    current["user"] = b
    assert client.get("/api/v1/config").json()["playlist_size"] == 50

    session.refresh(a)
    session.refresh(b)
    assert a.playlist_size == 100
    assert b.playlist_size == 50


def test_get_config_reads_current_user_and_setup_not_required(client, current, users):
    a, _ = users
    a.target_playlist_id = "dynA"
    current["user"] = a
    body = client.get("/api/v1/config").json()
    assert body["setup_required"] is False  # session user always has creds
    assert body["dynamic_playlist_id"] == "dynA"


# ────────────────────────────────────────────────────────────
# AC#7 (f) — get_blacklisted_ids(session, user_id) isolation
# ────────────────────────────────────────────────────────────


def test_get_blacklisted_ids_scoped_by_user(session, users):
    a, b = users
    session.add(TrackBlacklist(spotify_id="x", user_id=a.id, blacklisted_at="t"))
    session.add(TrackBlacklist(spotify_id="y", user_id=a.id, blacklisted_at="t"))
    session.add(TrackBlacklist(spotify_id="x", user_id=b.id, blacklisted_at="t"))
    session.commit()

    assert blacklist_service.get_blacklisted_ids(session, a.id) == {"x", "y"}
    assert blacklist_service.get_blacklisted_ids(session, b.id) == {"x"}


# ────────────────────────────────────────────────────────────
# AC#8 (g) — Dynamic playlist id stored per-user on User.target_playlist_id
# ────────────────────────────────────────────────────────────


def test_get_or_create_dynamic_playlist_reads_user(users):
    a, _ = users
    a.target_playlist_id = "dynA"
    mock_sp = MagicMock()
    mock_sp.playlist.return_value = {"id": "dynA"}
    assert spotify_service.get_or_create_dynamic_playlist(mock_sp, a) == "dynA"
    mock_sp.current_user_playlist_create.assert_not_called()


def test_create_dynamic_playlist_persists_onto_user_row(engine, session, users):
    a, _ = users
    a.target_playlist_id = None
    session.add(a)
    session.commit()

    mock_sp = MagicMock()
    mock_sp.me.return_value = {"id": "spotify_a"}
    mock_sp.current_user_playlists.return_value = {"items": [], "next": None}
    mock_sp.current_user_playlist_create.return_value = {"id": "new_dyn"}

    with patch("services.spotify.engine", engine):
        result = spotify_service.get_or_create_dynamic_playlist(mock_sp, a)

    assert result == "new_dyn"
    session.expire_all()
    assert session.get(User, a.id).target_playlist_id == "new_dyn"


# ────────────────────────────────────────────────────────────
# AC#4 (h)(i)(j) — One-shot idempotent migration + backfill
# ────────────────────────────────────────────────────────────


def _build_legacy_engine():
    """Build an engine holding the PRE-10.3 schema: a real `user` table plus legacy
    (un-scoped) config/playlist/track_blacklist/sync_log tables, via raw SQL."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    # The user table is the only new-shape table; build it from the model.
    User.__table__.create(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE config (id INTEGER PRIMARY KEY, client_id VARCHAR, "
            "client_secret VARCHAR, playlist_size INTEGER, cron_expr VARCHAR, "
            "spotify_token_json VARCHAR, dynamic_playlist_id VARCHAR, last_sync_at VARCHAR)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE playlist (id INTEGER PRIMARY KEY, spotify_id VARCHAR NOT NULL UNIQUE, "
            "name VARCHAR NOT NULL, is_included BOOLEAN NOT NULL, is_hidden BOOLEAN NOT NULL DEFAULT 0)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE track_blacklist (spotify_id VARCHAR PRIMARY KEY, blacklisted_at VARCHAR NOT NULL)"
        )
        conn.exec_driver_sql(
            "CREATE TABLE sync_log (id INTEGER PRIMARY KEY, status VARCHAR NOT NULL, "
            "track_count INTEGER, new_track_count INTEGER, error_message VARCHAR, timestamp VARCHAR NOT NULL)"
        )
    return engine


def _seed_legacy_data(engine):
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO config (playlist_size, cron_expr, dynamic_playlist_id, last_sync_at) "
            "VALUES (30, '0 5 * * *', 'dynX', '2026-01-01T00:00:00Z')"
        )
        conn.exec_driver_sql(
            "INSERT INTO playlist (spotify_id, name, is_included, is_hidden) "
            "VALUES ('p1', 'One', 1, 0), ('p2', 'Two', 0, 0)"
        )
        conn.exec_driver_sql(
            "INSERT INTO track_blacklist (spotify_id, blacklisted_at) VALUES ('bl1', 't'), ('bl2', 't')"
        )
        conn.exec_driver_sql(
            "INSERT INTO sync_log (status, timestamp) VALUES ('success', 't1'), ('failure', 't2')"
        )


def test_migration_backfills_rows_and_settings_to_owner():
    engine = _build_legacy_engine()
    _seed_legacy_data(engine)
    # The owner is the single/first User row (defaults: playlist_size=50, others None).
    with Session(engine) as s:
        owner = User(spotify_user_id="owner")
        s.add(owner)
        s.commit()
        owner_id = owner.id

    run_migrations(engine)

    with engine.connect() as conn:
        # All legacy data rows now owned by the owner.
        assert conn.execute(
            text("SELECT COUNT(*) FROM playlist WHERE user_id = :o"), {"o": owner_id}
        ).scalar() == 2
        assert conn.execute(
            text("SELECT COUNT(*) FROM track_blacklist WHERE user_id = :o"), {"o": owner_id}
        ).scalar() == 2
        assert conn.execute(
            text("SELECT COUNT(*) FROM sync_log WHERE user_id = :o"), {"o": owner_id}
        ).scalar() == 2
        # track_blacklist rebuilt to a composite PK (spotify_id, user_id).
        pk_cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(track_blacklist)").fetchall() if r[5] > 0]
        assert set(pk_cols) == {"spotify_id", "user_id"}

    # Config settings copied onto the owner User.
    with Session(engine) as s:
        owner = s.get(User, owner_id)
        assert owner.playlist_size == 30
        assert owner.cron_expr == "0 5 * * *"
        assert owner.target_playlist_id == "dynX"
        assert owner.last_sync_at == "2026-01-01T00:00:00Z"


def test_migration_preserves_per_user_uniqueness_after_backfill():
    """After the rebuild, a second user may blacklist the same id the owner has."""
    engine = _build_legacy_engine()
    _seed_legacy_data(engine)
    with Session(engine) as s:
        owner = User(spotify_user_id="owner")
        s.add(owner)
        s.commit()

    run_migrations(engine)

    with Session(engine) as s:
        other = User(spotify_user_id="other")
        s.add(other)
        s.commit()
        # 'bl1' already owned by the owner — a different user can reuse it.
        s.add(TrackBlacklist(spotify_id="bl1", user_id=other.id, blacklisted_at="t"))
        s.commit()
        rows = s.exec(select(TrackBlacklist).where(TrackBlacklist.spotify_id == "bl1")).all()
        assert len(rows) == 2


def test_migration_is_idempotent():
    engine = _build_legacy_engine()
    _seed_legacy_data(engine)
    with Session(engine) as s:
        owner = User(spotify_user_id="owner")
        s.add(owner)
        s.commit()
        owner_id = owner.id

    run_migrations(engine)
    # A user-edited setting after the first migration must NOT be clobbered by a re-run.
    with Session(engine) as s:
        o = s.get(User, owner_id)
        o.playlist_size = 99
        s.add(o)
        s.commit()

    run_migrations(engine)  # second run — no error, no clobber, no row duplication

    with engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT COUNT(*) FROM playlist").scalar() == 2
        assert conn.exec_driver_sql("SELECT COUNT(*) FROM track_blacklist").scalar() == 2
    with Session(engine) as s:
        assert s.get(User, owner_id).playlist_size == 99


def test_migration_adds_last_sync_at_to_legacy_user_table():
    """Real prod upgrade path: 10.1 created `user` WITHOUT last_sync_at, and
    `create_all` never alters it. The migration must ADD COLUMN it (no owner needed),
    otherwise the lifespan's `SELECT user.*` crashes on boot."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    # Legacy user table: the 10.1 shape, missing last_sync_at.
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE user (id INTEGER PRIMARY KEY, spotify_user_id VARCHAR UNIQUE, "
            "display_name VARCHAR, client_id VARCHAR, client_secret VARCHAR, "
            "token_json VARCHAR, playlist_size INTEGER DEFAULT 50, cron_expr VARCHAR, "
            "target_playlist_id VARCHAR, created_at VARCHAR)"
        )
        conn.exec_driver_sql("INSERT INTO user (spotify_user_id) VALUES ('owner')")

    with engine.connect() as conn:
        cols = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(user)").fetchall()}
    assert "last_sync_at" not in cols  # red: column truly absent before migration

    run_migrations(engine)

    with engine.connect() as conn:
        cols = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(user)").fetchall()}
    assert "last_sync_at" in cols
    # The select that crashed on boot now works.
    with Session(engine) as s:
        assert s.exec(select(User)).first().last_sync_at is None

    run_migrations(engine)  # idempotent — re-running must not raise


def test_migration_no_owner_is_safe_noop_on_fresh_schema():
    """Fresh install: full new schema via create_all, no users, no legacy config."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    run_migrations(engine)  # must not raise

    # Schema is intact and usable: a scoped Playlist insert works.
    with Session(engine) as s:
        s.add(User(spotify_user_id="fresh"))
        s.commit()
        s.add(Playlist(user_id=1, spotify_id="p", name="P"))
        s.commit()
        assert s.exec(select(Playlist)).first().user_id == 1
