import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from dependencies import get_current_user
from models.user import User
from models.sync_log import SyncLog


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
    def get_session_override():
        return session
    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_current_user] = lambda: User(id=1, spotify_user_id="test_user")
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_get_status_no_syncs_returns_null(client):
    r = client.get("/api/v1/sync/status")
    assert r.status_code == 200
    assert r.json() is None


def test_get_status_after_success(client, session):
    session.add(SyncLog(user_id=1, status="success", track_count=42, error_message=None, timestamp="2026-05-20T10:00:00Z"))
    session.commit()
    r = client.get("/api/v1/sync/status")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["track_count"] == 42
    assert data["error_message"] is None


def test_get_status_after_failure(client, session):
    session.add(SyncLog(user_id=1, status="failure", track_count=None, error_message="Token expired", timestamp="2026-05-20T11:00:00Z"))
    session.commit()
    r = client.get("/api/v1/sync/status")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "failure"
    assert data["error_message"] == "Token expired"
    assert data["track_count"] is None


def test_get_status_returns_most_recent(client, session):
    session.add(SyncLog(user_id=1, status="failure", track_count=None, error_message="Old error", timestamp="2026-05-19T10:00:00Z"))
    session.add(SyncLog(user_id=1, status="success", track_count=30, error_message=None, timestamp="2026-05-20T10:00:00Z"))
    session.commit()
    r = client.get("/api/v1/sync/status")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["track_count"] == 30
