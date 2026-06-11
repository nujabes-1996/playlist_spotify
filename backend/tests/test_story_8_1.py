import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from dependencies import get_current_user
from models.user import User
from models.track_blacklist import TrackBlacklist


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


def test_get_empty_returns_empty_array(client):
    r = client.get("/api/v1/blacklist")
    assert r.status_code == 200
    assert r.json() == []


def test_post_inserts_and_returns_201(client, session):
    r = client.post("/api/v1/blacklist", json={"spotify_id": "abc"})
    assert r.status_code == 201
    body = r.json()
    assert body["spotify_id"] == "abc"
    assert isinstance(body["blacklisted_at"], str) and len(body["blacklisted_at"]) > 0

    row = session.exec(
        select(TrackBlacklist).where(TrackBlacklist.spotify_id == "abc")
    ).first()
    assert row is not None
    assert row.blacklisted_at == body["blacklisted_at"]


def test_post_duplicate_returns_200_idempotent_no_overwrite(client, session):
    fixed_ts = "2026-01-01T00:00:00"
    session.add(TrackBlacklist(user_id=1, spotify_id="abc", blacklisted_at=fixed_ts))
    session.commit()

    r = client.post("/api/v1/blacklist", json={"spotify_id": "abc"})
    assert r.status_code == 200
    body = r.json()
    assert body["spotify_id"] == "abc"
    assert body["blacklisted_at"] == fixed_ts


def test_get_returns_rows_sorted_desc(client, session):
    session.add(TrackBlacklist(user_id=1, spotify_id="middle", blacklisted_at="2026-05-19T10:00:00"))
    session.add(TrackBlacklist(user_id=1, spotify_id="newest", blacklisted_at="2026-05-20T10:00:00"))
    session.add(TrackBlacklist(user_id=1, spotify_id="oldest", blacklisted_at="2026-05-18T10:00:00"))
    session.commit()

    r = client.get("/api/v1/blacklist")
    assert r.status_code == 200
    ids = [row["spotify_id"] for row in r.json()]
    assert ids == ["newest", "middle", "oldest"]


def test_delete_existing_returns_204_and_row_gone(client, session):
    session.add(TrackBlacklist(user_id=1, spotify_id="abc", blacklisted_at="2026-05-20T10:00:00"))
    session.commit()

    r = client.delete("/api/v1/blacklist/abc")
    assert r.status_code == 204
    assert r.content == b""

    r2 = client.get("/api/v1/blacklist")
    assert r2.status_code == 200
    assert r2.json() == []


def test_delete_nonexistent_returns_204_idempotent(client):
    r = client.delete("/api/v1/blacklist/does-not-exist")
    assert r.status_code == 204
    assert r.content == b""


def test_post_missing_spotify_id_returns_422(client):
    r = client.post("/api/v1/blacklist", json={})
    assert r.status_code == 422


def test_post_empty_spotify_id_returns_422(client):
    r = client.post("/api/v1/blacklist", json={"spotify_id": ""})
    assert r.status_code == 422
