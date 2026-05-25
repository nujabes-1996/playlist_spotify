import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from models.config import Config


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


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_config_exposes_dynamic_playlist_id(client, session):
    session.add(
        Config(
            client_id="cid",
            client_secret="csec",
            playlist_size=50,
            dynamic_playlist_id="abc123",
        )
    )
    session.commit()

    r = client.get("/api/v1/config")
    assert r.status_code == 200
    body = r.json()
    assert body["dynamic_playlist_id"] == "abc123"
    assert body["setup_required"] is False


def test_config_dynamic_playlist_id_defaults_null(client):
    # No Config row: setup_required branch
    r = client.get("/api/v1/config")
    assert r.status_code == 200
    body = r.json()
    assert body["setup_required"] is True
    assert body["dynamic_playlist_id"] is None
