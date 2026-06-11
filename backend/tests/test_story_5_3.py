import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from dependencies import get_current_user
from models.user import User


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


def test_stream_returns_sse_content_type(client):
    async def _mock_stream():
        yield "event: sync_complete\ndata: {\"status\": \"success\", \"track_count\": 0, \"timestamp\": \"2026-01-01T00:00:00Z\"}\n\n"

    with patch("routers.sync._run_sync_stream", return_value=_mock_stream()):
        r = client.get("/api/v1/sync/stream")
    assert "text/event-stream" in r.headers["content-type"]


def test_stream_emits_sync_complete_on_success(client):
    async def _mock_stream():
        yield "event: sync_log\ndata: {\"level\": \"info\", \"message\": \"Starting\", \"timestamp\": \"2026-01-01T00:00:00Z\"}\n\n"
        yield "event: sync_complete\ndata: {\"status\": \"success\", \"track_count\": 10, \"timestamp\": \"2026-01-01T00:00:01Z\"}\n\n"

    with patch("routers.sync._run_sync_stream", return_value=_mock_stream()):
        r = client.get("/api/v1/sync/stream")
    assert r.status_code == 200
    body = r.text
    assert "event: sync_complete" in body
    assert "sync_log" in body


def test_stream_emits_sync_error_on_failure(client):
    async def _mock_stream():
        yield "event: sync_error\ndata: {\"status\": \"error\", \"message\": \"Token expired\", \"timestamp\": \"2026-01-01T00:00:00Z\"}\n\n"

    with patch("routers.sync._run_sync_stream", return_value=_mock_stream()):
        r = client.get("/api/v1/sync/stream")
    assert r.status_code == 200
    assert "event: sync_error" in r.text
    assert "Token expired" in r.text
