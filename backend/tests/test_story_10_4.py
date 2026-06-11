"""Story 10.4 — Per-User Scheduler Jobs.

One APScheduler job per user (`sync_{user_id}`), each driven by that user's own
cron_expr, each running run_sync(user_id) as that user. Replaces the single global
`sync_job` + _resolve_scheduled_user() bridge from 10.2/10.3.
"""
import pytest
from unittest.mock import patch, MagicMock
from apscheduler.triggers.cron import CronTrigger
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from dependencies import get_current_user
from models.playlist import Playlist
from models.sync_log import SyncLog
from models.user import User
import scheduler as scheduler_module
import services.sync_engine as sync_engine


# ────────────────────────────────────────────────────────────
# (a) Per-user job registration — two users → two distinct jobs
# ────────────────────────────────────────────────────────────

def test_bootstrap_user_job_registers_per_user_jobs():
    with patch("scheduler.scheduler.add_job") as mock_add, \
         patch("scheduler.scheduler.get_job", return_value=None):
        scheduler_module.bootstrap_user_job(1, "0 * * * *")
        scheduler_module.bootstrap_user_job(2, "30 3 * * *")

    assert mock_add.call_count == 2

    first = mock_add.call_args_list[0]
    assert first.kwargs["id"] == "sync_1"
    assert first.kwargs["args"] == [1]
    assert first.kwargs["replace_existing"] is True
    assert first.kwargs["max_instances"] == 1
    assert first.kwargs["coalesce"] is True
    assert isinstance(first.args[1], CronTrigger)

    second = mock_add.call_args_list[1]
    assert second.kwargs["id"] == "sync_2"
    assert second.kwargs["args"] == [2]
    assert isinstance(second.args[1], CronTrigger)


def test_bootstrap_user_job_passes_run_sync_callable():
    with patch("scheduler.scheduler.add_job") as mock_add, \
         patch("scheduler.scheduler.get_job", return_value=None):
        scheduler_module.bootstrap_user_job(1, "0 * * * *")
    assert mock_add.call_args.args[0] is sync_engine.run_sync


# ────────────────────────────────────────────────────────────
# (b) Clearing cron removes only that user's job
# ────────────────────────────────────────────────────────────

def test_bootstrap_user_job_none_removes_only_that_job():
    mock_job = MagicMock()
    with patch("scheduler.scheduler.get_job", return_value=mock_job) as mock_get, \
         patch("scheduler.scheduler.remove_job") as mock_remove, \
         patch("scheduler.scheduler.add_job") as mock_add:
        scheduler_module.bootstrap_user_job(1, None)

    mock_add.assert_not_called()
    mock_get.assert_called_once_with("sync_1")
    mock_remove.assert_called_once_with("sync_1")


def test_bootstrap_user_job_none_no_existing_job_does_nothing():
    with patch("scheduler.scheduler.get_job", return_value=None), \
         patch("scheduler.scheduler.remove_job") as mock_remove, \
         patch("scheduler.scheduler.add_job") as mock_add:
        scheduler_module.bootstrap_user_job(2, None)

    mock_add.assert_not_called()
    mock_remove.assert_not_called()


# ────────────────────────────────────────────────────────────
# (d) bootstrap_all_jobs — registers cron'd users, removes cron-less
# ────────────────────────────────────────────────────────────

def test_bootstrap_all_jobs_registers_and_removes():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(id=1, spotify_user_id="u1", cron_expr="0 * * * *"))
        session.add(User(id=2, spotify_user_id="u2", cron_expr=None))
        session.add(User(id=3, spotify_user_id="u3", cron_expr="30 3 * * *"))
        session.commit()

    with patch("scheduler.engine", engine), \
         patch("scheduler.scheduler.add_job") as mock_add, \
         patch("scheduler.scheduler.get_job", return_value=None), \
         patch("scheduler.scheduler.remove_job"):
        scheduler_module.bootstrap_all_jobs()

    added_ids = {c.kwargs["id"] for c in mock_add.call_args_list}
    assert added_ids == {"sync_1", "sync_3"}  # cron'd users only; user 2 not added


def test_bootstrap_all_jobs_empty_db_registers_nothing():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    with patch("scheduler.engine", engine), \
         patch("scheduler.scheduler.add_job") as mock_add, \
         patch("scheduler.scheduler.get_job", return_value=None), \
         patch("scheduler.scheduler.remove_job") as mock_remove:
        scheduler_module.bootstrap_all_jobs()

    mock_add.assert_not_called()
    mock_remove.assert_not_called()


# ────────────────────────────────────────────────────────────
# (e) purge_legacy_global_job — drops pre-10.4 `sync_job`
# ────────────────────────────────────────────────────────────

def test_purge_legacy_global_job_removes_when_present():
    with patch("scheduler.scheduler.get_job", return_value=MagicMock()) as mock_get, \
         patch("scheduler.scheduler.remove_job") as mock_remove:
        scheduler_module.purge_legacy_global_job()

    mock_get.assert_called_once_with("sync_job")
    mock_remove.assert_called_once_with("sync_job")


def test_purge_legacy_global_job_noop_when_absent():
    with patch("scheduler.scheduler.get_job", return_value=None), \
         patch("scheduler.scheduler.remove_job") as mock_remove:
        scheduler_module.purge_legacy_global_job()

    mock_remove.assert_not_called()


# ────────────────────────────────────────────────────────────
# (c) run_sync(user_id) runs as that user
# ────────────────────────────────────────────────────────────

PLAYLIST_TRACKS = [
    {"spotify_id": "t1", "uri": "spotify:track:t1", "added_at": "2026-05-10T00:00:00Z"},
    {"spotify_id": "t2", "uri": "spotify:track:t2", "added_at": "2026-05-08T00:00:00Z"},
]


@pytest.fixture(name="two_user_engine")
def two_user_engine_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(id=1, spotify_user_id="u1", client_id="c", client_secret="s",
                         token_json="{}", playlist_size=2, target_playlist_id="dyn_1"))
        session.add(User(id=2, spotify_user_id="u2", client_id="c", client_secret="s",
                         token_json="{}", playlist_size=2, target_playlist_id="dyn_2"))
        session.add(Playlist(user_id=2, spotify_id="pl2", name="Mix", is_included=True))
        session.commit()
    return engine


def test_run_sync_runs_as_passed_user(two_user_engine):
    mock_sp = MagicMock()
    with (
        patch("services.sync_engine.engine", two_user_engine),
        patch("services.sync_engine.spotify_service.get_authenticated_client", return_value=mock_sp),
        patch("services.sync_engine.spotify_service.get_playlist_tracks", return_value=PLAYLIST_TRACKS),
        patch("services.sync_engine.spotify_service.get_or_create_dynamic_playlist", return_value="dyn_2"),
        patch("services.sync_engine.spotify_service.replace_playlist_tracks"),
    ):
        result = sync_engine.run_sync(2)

    assert result["status"] == "success"

    with Session(two_user_engine) as session:
        logs = session.exec(select(SyncLog)).all()
        assert len(logs) == 1
        assert logs[0].user_id == 2  # written against the passed user
        u1 = session.get(User, 1)
        u2 = session.get(User, 2)
        assert u2.last_sync_at is not None  # user 2 synced
        assert u1.last_sync_at is None  # user 1 untouched


def test_run_sync_missing_user_is_noop(two_user_engine):
    with patch("services.sync_engine.engine", two_user_engine):
        result = sync_engine.run_sync(999)

    assert result == {"status": "skipped", "reason": "user not found"}
    with Session(two_user_engine) as session:
        assert session.exec(select(SyncLog)).all() == []


# ────────────────────────────────────────────────────────────
# (f) PATCH /config re-bootstraps only the acting user's job
# ────────────────────────────────────────────────────────────

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    session.add(User(id=1, spotify_user_id="test_user", client_id="id", client_secret="secret"))
    session.commit()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: session.get(User, 1)
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_patch_config_bootstraps_acting_user_job(client):
    with patch("routers.config.bootstrap_user_job") as mock_bs:
        r = client.patch("/api/v1/config", json={"cron_expr": "0 0 * * *"})
    assert r.status_code == 200
    mock_bs.assert_called_once_with(1, "0 0 * * *")


def test_patch_config_clear_cron_removes_acting_user_job(client):
    with patch("routers.config.bootstrap_user_job"):
        client.patch("/api/v1/config", json={"cron_expr": "0 * * * *"})
    with patch("routers.config.bootstrap_user_job") as mock_bs:
        r = client.patch("/api/v1/config", json={"cron_expr": None})
    assert r.status_code == 200
    mock_bs.assert_called_once_with(1, None)
