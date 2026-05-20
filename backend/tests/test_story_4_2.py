import pytest
from unittest.mock import patch
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


def _seed_config(session, cron_expr=None):
    config = Config(client_id="id", client_secret="secret", playlist_size=50, cron_expr=cron_expr)
    session.add(config)
    session.commit()
    session.refresh(config)
    return config


def test_put_config_with_cron_calls_bootstrap(client, session):
    with patch("routers.config.bootstrap_scheduler") as mock_bs:
        r = client.put("/api/v1/config", json={"client_id": "a", "client_secret": "b", "cron_expr": "0 */6 * * *"})
    assert r.status_code == 200
    mock_bs.assert_called_once_with("0 */6 * * *")


def test_put_config_without_cron_calls_bootstrap_none(client, session):
    with patch("routers.config.bootstrap_scheduler") as mock_bs:
        r = client.put("/api/v1/config", json={"client_id": "a", "client_secret": "b"})
    assert r.status_code == 200
    mock_bs.assert_called_once_with(None)


def test_patch_with_valid_cron_calls_bootstrap(client, session):
    _seed_config(session)
    with patch("routers.config.bootstrap_scheduler") as mock_bs:
        r = client.patch("/api/v1/config", json={"cron_expr": "0 0 * * *"})
    assert r.status_code == 200
    mock_bs.assert_called_once_with("0 0 * * *")


def test_patch_clear_cron_calls_bootstrap_none(client, session):
    _seed_config(session, cron_expr="0 * * * *")
    with patch("routers.config.bootstrap_scheduler") as mock_bs:
        r = client.patch("/api/v1/config", json={"cron_expr": None})
    assert r.status_code == 200
    mock_bs.assert_called_once_with(None)


def test_patch_without_cron_key_skips_bootstrap(client, session):
    _seed_config(session, cron_expr="0 * * * *")
    with patch("routers.config.bootstrap_scheduler") as mock_bs:
        r = client.patch("/api/v1/config", json={"playlist_size": 75})
    assert r.status_code == 200
    mock_bs.assert_not_called()


def test_invalid_cron_put_returns_400(client, session):
    with patch("routers.config.bootstrap_scheduler") as mock_bs:
        r = client.put("/api/v1/config", json={"client_id": "a", "client_secret": "b", "cron_expr": "not-a-cron"})
    assert r.status_code == 400
    mock_bs.assert_not_called()


def test_invalid_cron_patch_returns_400(client, session):
    _seed_config(session)
    with patch("routers.config.bootstrap_scheduler") as mock_bs:
        r = client.patch("/api/v1/config", json={"cron_expr": "not-a-cron"})
    assert r.status_code == 400
    mock_bs.assert_not_called()


def test_invalid_cron_does_not_corrupt_db(client, session):
    _seed_config(session, cron_expr="0 * * * *")
    with patch("routers.config.bootstrap_scheduler"):
        client.patch("/api/v1/config", json={"cron_expr": "not-a-cron"})
    r = client.get("/api/v1/config")
    assert r.json()["cron_expr"] == "0 * * * *"
