import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from dependencies import get_current_user
from models.user import User


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


@pytest.fixture(name="user")
def user_fixture(session: Session):
    u = User(id=1, spotify_user_id="test_user", client_id="cid", client_secret="csec")
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


def test_config_exposes_dynamic_playlist_id(client, session, user):
    # Story 10.3: dynamic playlist id lives on the user's target_playlist_id.
    user.target_playlist_id = "abc123"
    session.add(user)
    session.commit()

    r = client.get("/api/v1/config")
    assert r.status_code == 200
    body = r.json()
    assert body["dynamic_playlist_id"] == "abc123"
    assert body["setup_required"] is False


def test_config_dynamic_playlist_id_defaults_null(client):
    # A logged-in user with no dynamic playlist yet: id is null, but a session user
    # always has credentials so setup is not required.
    r = client.get("/api/v1/config")
    assert r.status_code == 200
    body = r.json()
    assert body["setup_required"] is False
    assert body["dynamic_playlist_id"] is None
