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


def test_get_logs_empty_returns_empty_array(client):
    r = client.get("/api/v1/sync/logs")
    assert r.status_code == 200
    assert r.json() == []


def test_get_logs_returns_entries_ordered_desc(client, session):
    session.add(SyncLog(user_id=1, status="success", track_count=10, timestamp="2026-05-01T10:00:00Z"))
    session.add(SyncLog(user_id=1, status="success", track_count=20, timestamp="2026-05-02T10:00:00Z"))
    session.commit()
    r = client.get("/api/v1/sync/logs")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["timestamp"] > data[1]["timestamp"]


def test_get_logs_success_entry_shape(client, session):
    session.add(SyncLog(user_id=1, status="success", track_count=42, error_message=None, timestamp="2026-05-01T12:00:00Z"))
    session.commit()
    r = client.get("/api/v1/sync/logs")
    assert r.status_code == 200
    entry = r.json()[0]
    assert entry["status"] == "success"
    assert entry["track_count"] == 42
    assert entry["error_message"] is None
    assert "timestamp" in entry
    assert "id" in entry


def test_get_logs_failure_entry_shape(client, session):
    session.add(SyncLog(user_id=1, status="failure", track_count=None, error_message="Token expired", timestamp="2026-05-01T13:00:00Z"))
    session.commit()
    r = client.get("/api/v1/sync/logs")
    assert r.status_code == 200
    entry = r.json()[0]
    assert entry["status"] == "failure"
    assert entry["track_count"] is None
    assert entry["error_message"] == "Token expired"
