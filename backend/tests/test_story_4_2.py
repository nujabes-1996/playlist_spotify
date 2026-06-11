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


@pytest.fixture(name="user")
def user_fixture(session: Session):
    u = User(id=1, spotify_user_id="test_user", client_id="id", client_secret="secret")
    session.add(u)
    session.commit()
    return u


@pytest.fixture(name="client")
def client_fixture(session: Session, user: User):
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: session.get(User, 1)
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# Story 10.3 removed PUT /config (credentials now flow through /auth/connect). The
# scheduler re-bootstrap on PATCH /config is sourced from the current user's cron_expr.


def test_patch_with_valid_cron_calls_bootstrap(client):
    with patch("routers.config.bootstrap_user_job") as mock_bs:
        r = client.patch("/api/v1/config", json={"cron_expr": "0 0 * * *"})
    assert r.status_code == 200
    mock_bs.assert_called_once_with(1, "0 0 * * *")


def test_patch_clear_cron_calls_bootstrap_none(client):
    with patch("routers.config.bootstrap_user_job"):
        client.patch("/api/v1/config", json={"cron_expr": "0 * * * *"})
    with patch("routers.config.bootstrap_user_job") as mock_bs:
        r = client.patch("/api/v1/config", json={"cron_expr": None})
    assert r.status_code == 200
    mock_bs.assert_called_once_with(1, None)


def test_patch_without_cron_key_skips_bootstrap(client):
    with patch("routers.config.bootstrap_user_job"):
        client.patch("/api/v1/config", json={"cron_expr": "0 * * * *"})
    with patch("routers.config.bootstrap_user_job") as mock_bs:
        r = client.patch("/api/v1/config", json={"playlist_size": 75})
    assert r.status_code == 200
    mock_bs.assert_not_called()


def test_invalid_cron_patch_returns_400(client):
    with patch("routers.config.bootstrap_user_job") as mock_bs:
        r = client.patch("/api/v1/config", json={"cron_expr": "not-a-cron"})
    assert r.status_code == 400
    mock_bs.assert_not_called()


def test_invalid_cron_does_not_corrupt_db(client):
    with patch("routers.config.bootstrap_user_job"):
        client.patch("/api/v1/config", json={"cron_expr": "0 * * * *"})
        client.patch("/api/v1/config", json={"cron_expr": "not-a-cron"})
    r = client.get("/api/v1/config")
    assert r.json()["cron_expr"] == "0 * * * *"
