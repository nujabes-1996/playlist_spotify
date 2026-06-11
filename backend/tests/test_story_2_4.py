import pytest
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
    # Story 10.3: settings live on the User row. The user is persisted so PATCH
    # mutations survive across requests within the shared session.
    u = User(id=1, spotify_user_id="test_user", client_id="id", client_secret="secret")
    session.add(u)
    session.commit()
    return u


@pytest.fixture(name="client")
def client_fixture(session: Session, user: User):
    app.dependency_overrides[get_session] = lambda: session
    # Resolve the live persisted row each call so reads reflect committed writes.
    app.dependency_overrides[get_current_user] = lambda: session.get(User, 1)
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_patch_updates_playlist_size(client):
    r = client.patch("/api/v1/config", json={"playlist_size": 100})
    assert r.status_code == 200
    assert r.json()["playlist_size"] == 100


def test_patch_updates_cron_expr(client):
    r = client.patch("/api/v1/config", json={"cron_expr": "0 */6 * * *"})
    assert r.status_code == 200
    assert r.json()["cron_expr"] == "0 */6 * * *"


def test_patch_null_cron_clears_it(client):
    client.patch("/api/v1/config", json={"cron_expr": "0 * * * *"})
    r = client.patch("/api/v1/config", json={"cron_expr": None})
    assert r.status_code == 200
    assert r.json()["cron_expr"] is None


def test_patch_without_cron_key_leaves_existing(client):
    client.patch("/api/v1/config", json={"cron_expr": "0 * * * *"})
    r = client.patch("/api/v1/config", json={"playlist_size": 75})
    assert r.status_code == 200
    assert r.json()["cron_expr"] == "0 * * * *"  # unchanged


def test_get_config_reflects_patch(client):
    client.patch("/api/v1/config", json={"playlist_size": 200, "cron_expr": "0 0 * * *"})
    r = client.get("/api/v1/config")
    assert r.json()["playlist_size"] == 200
    assert r.json()["cron_expr"] == "0 0 * * *"
    assert r.json()["setup_required"] is False  # logged-in user always has creds
