import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(name="client")
def client_fixture():
    with TestClient(app) as client:
        yield client


def test_sync_run_success(client):
    with patch(
        "routers.sync.sync_engine.run_sync",
        return_value={"status": "success", "track_count": 42},
    ):
        response = client.post("/api/v1/sync/run")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["track_count"] == 42


def test_sync_run_no_playlists_returns_400(client):
    with patch(
        "routers.sync.sync_engine.run_sync",
        side_effect=ValueError("No playlists selected"),
    ):
        response = client.post("/api/v1/sync/run")
    assert response.status_code == 400
    assert "No playlists selected" in response.json()["detail"]


def test_sync_run_spotify_error_returns_500(client):
    with patch(
        "routers.sync.sync_engine.run_sync",
        side_effect=Exception("Spotify 500"),
    ):
        response = client.post("/api/v1/sync/run")
    assert response.status_code == 500
    assert "Spotify 500" in response.json()["detail"]
