"""Tests for Story 1.3: APScheduler & SQLiteCacheHandler Foundation."""
import json
import pytest
from unittest.mock import patch
from sqlmodel import SQLModel, create_engine, Session

import models  # noqa: F401 — ensure all table metadata is registered before create_all

# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_engine():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


# ---------------------------------------------------------------------------
# AC3 & AC4 — SQLiteCacheHandler
# ---------------------------------------------------------------------------

class TestSQLiteCacheHandler:
    def _make_handler(self, engine):
        """Instantiate SQLiteCacheHandler with test engine injected."""
        import services.token_manager as tm
        original_engine = tm.engine

        tm.engine = engine
        handler = tm.SQLiteCacheHandler()

        yield handler

        tm.engine = original_engine

    def test_get_cached_token_returns_none_when_no_row(self, test_engine):
        """AC4: get_cached_token() must return None gracefully when no data."""
        import services.token_manager as tm
        original_engine = tm.engine
        tm.engine = test_engine
        try:
            handler = tm.SQLiteCacheHandler()
            result = handler.get_cached_token()
            assert result is None
        finally:
            tm.engine = original_engine

    def test_get_cached_token_returns_none_when_token_json_is_null(self, test_engine):
        """AC4: returns None when Config row exists but spotify_token_json is None."""
        from models.config import Config
        import services.token_manager as tm
        original_engine = tm.engine
        tm.engine = test_engine

        with Session(test_engine) as session:
            session.add(Config())
            session.commit()

        try:
            handler = tm.SQLiteCacheHandler()
            result = handler.get_cached_token()
            assert result is None
        finally:
            tm.engine = original_engine

    def test_save_token_creates_row_and_get_cached_token_returns_it(self, test_engine):
        """AC3: save_token_to_cache writes JSON; get_cached_token reads it back."""
        import services.token_manager as tm
        original_engine = tm.engine
        tm.engine = test_engine

        token = {"access_token": "abc123", "token_type": "Bearer", "expires_in": 3600}
        try:
            handler = tm.SQLiteCacheHandler()
            handler.save_token_to_cache(token)
            result = handler.get_cached_token()
            assert result == token
        finally:
            tm.engine = original_engine

    def test_save_token_upserts_existing_row(self, test_engine):
        """AC3: save_token_to_cache upserts — updates existing Config row."""
        from models.config import Config
        import services.token_manager as tm
        original_engine = tm.engine
        tm.engine = test_engine

        with Session(test_engine) as session:
            session.add(Config(client_id="test_client"))
            session.commit()

        token = {"access_token": "xyz789"}
        try:
            handler = tm.SQLiteCacheHandler()
            handler.save_token_to_cache(token)
            result = handler.get_cached_token()
            assert result == token

            # Ensure we still only have one row
            with Session(test_engine) as session:
                from sqlmodel import select
                configs = session.exec(select(Config)).all()
                assert len(configs) == 1
                assert configs[0].client_id == "test_client"
        finally:
            tm.engine = original_engine

    def test_save_token_serializes_as_json(self, test_engine):
        """AC3: spotify_token_json column stores JSON string."""
        from models.config import Config
        from sqlmodel import select
        import services.token_manager as tm
        original_engine = tm.engine
        tm.engine = test_engine

        token = {"access_token": "tok", "expires_in": 3600}
        try:
            handler = tm.SQLiteCacheHandler()
            handler.save_token_to_cache(token)

            with Session(test_engine) as session:
                config = session.exec(select(Config)).first()
                assert config.spotify_token_json == json.dumps(token)
        finally:
            tm.engine = original_engine


# ---------------------------------------------------------------------------
# AC1 & AC2 — Scheduler configuration
# ---------------------------------------------------------------------------

class TestSchedulerConfiguration:
    def test_scheduler_uses_sqlalchemy_jobstore(self):
        """AC1: scheduler singleton must use SQLAlchemyJobStore, not MemoryJobStore."""
        from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
        from scheduler import scheduler
        assert "default" in scheduler._jobstores
        assert isinstance(scheduler._jobstores["default"], SQLAlchemyJobStore)

    def test_scheduler_jobstore_url(self):
        """AC1: SQLAlchemyJobStore must point to sqlite:////data/app.db."""
        from scheduler import scheduler
        jobstore = scheduler._jobstores["default"]
        assert "data/app.db" in str(jobstore.engine.url)

    def test_scheduler_is_background_scheduler(self):
        """AC1: must be BackgroundScheduler (APScheduler 3.x)."""
        from apscheduler.schedulers.background import BackgroundScheduler
        from scheduler import scheduler
        assert isinstance(scheduler, BackgroundScheduler)


# ---------------------------------------------------------------------------
# AC2 — apscheduler_jobs table (integration, needs real DB)
# ---------------------------------------------------------------------------

class TestAPSchedulerJobsTable:
    def test_apscheduler_jobs_table_created_on_start(self, tmp_path):
        """AC2: starting scheduler creates apscheduler_jobs table in SQLite DB."""
        import sqlite3
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

        db_path = tmp_path / "test.db"
        url = f"sqlite:///{db_path}"

        sched = BackgroundScheduler(
            jobstores={"default": SQLAlchemyJobStore(url=url)}
        )
        sched.start()
        try:
            conn = sqlite3.connect(str(db_path))
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            conn.close()
            assert "apscheduler_jobs" in tables
        finally:
            sched.shutdown(wait=False)


# ---------------------------------------------------------------------------
# AC4 — No errors on startup (regression: /health endpoint)
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_endpoint_returns_ok(self):
        """AC4 regression: /health must still return {'status': 'ok'}."""
        from fastapi.testclient import TestClient
        # Patch scheduler start/shutdown to avoid real DB and thread issues in tests
        with patch("scheduler.scheduler.start"), patch("scheduler.scheduler.shutdown"):
            from main import app
            client = TestClient(app)
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
