import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from models.config import Config


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
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def _seed_config(session: Session, playlist_size: int = 50, cron_expr: str | None = None) -> Config:
    config = Config(client_id="id", client_secret="secret", playlist_size=playlist_size, cron_expr=cron_expr)
    session.add(config)
    session.commit()
    session.refresh(config)
    return config


def test_patch_updates_playlist_size(client, session):
    _seed_config(session)
    r = client.patch("/api/v1/config", json={"playlist_size": 100})
    assert r.status_code == 200
    assert r.json()["playlist_size"] == 100


def test_patch_updates_cron_expr(client, session):
    _seed_config(session)
    r = client.patch("/api/v1/config", json={"cron_expr": "0 */6 * * *"})
    assert r.status_code == 200
    assert r.json()["cron_expr"] == "0 */6 * * *"


def test_patch_null_cron_clears_it(client, session):
    _seed_config(session, cron_expr="0 * * * *")
    r = client.patch("/api/v1/config", json={"cron_expr": None})
    assert r.status_code == 200
    assert r.json()["cron_expr"] is None


def test_patch_without_cron_key_leaves_existing(client, session):
    _seed_config(session, cron_expr="0 * * * *")
    r = client.patch("/api/v1/config", json={"playlist_size": 75})
    assert r.status_code == 200
    assert r.json()["cron_expr"] == "0 * * * *"  # unchanged


def test_patch_no_config_row_returns_400(client):
    r = client.patch("/api/v1/config", json={"playlist_size": 50})
    assert r.status_code == 400


def test_get_config_reflects_patch(client, session):
    _seed_config(session, playlist_size=50)
    client.patch("/api/v1/config", json={"playlist_size": 200, "cron_expr": "0 0 * * *"})
    r = client.get("/api/v1/config")
    assert r.json()["playlist_size"] == 200
    assert r.json()["cron_expr"] == "0 0 * * *"
