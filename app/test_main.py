import pytest

import main
from main import NOTES, app


@pytest.fixture
def client():
    NOTES.clear()
    app.config["TESTING"] = True
    return app.test_client()


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.get_json()["service"] == "notes-service"


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok"
    assert body["uptime_seconds"] >= 0


def test_ready(client):
    r = client.get("/ready")
    assert r.status_code == 200


def test_ready_fails_when_flag_set(client, monkeypatch):
    monkeypatch.setattr(main, "FAIL_READINESS", True)
    r = client.get("/ready")
    assert r.status_code == 503


def test_version(client):
    r = client.get("/version")
    assert r.status_code == 200
    assert "version" in r.get_json()
    assert r.headers["X-App-Version"] == r.get_json()["version"]


def test_request_id_is_echoed(client):
    r = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert r.headers["X-Request-ID"] == "abc123"


def test_add_and_list_notes(client):
    r = client.post("/notes", json={"text": "hello devops"})
    assert r.status_code == 201
    assert r.get_json()["id"] == 0
    r = client.get("/notes")
    assert r.get_json() == {"notes": ["hello devops"], "count": 1}


def test_add_note_requires_text(client):
    r = client.post("/notes", json={})
    assert r.status_code == 400


def test_add_note_rejects_too_long(client):
    r = client.post("/notes", json={"text": "x" * (main.MAX_NOTE_LENGTH + 1)})
    assert r.status_code == 400


def test_delete_note(client):
    client.post("/notes", json={"text": "first"})
    client.post("/notes", json={"text": "second"})
    r = client.delete("/notes/0")
    assert r.status_code == 200
    assert client.get("/notes").get_json()["notes"] == ["second"]


def test_delete_missing_note(client):
    r = client.delete("/notes/5")
    assert r.status_code == 404


def test_unknown_route_returns_json_404(client):
    r = client.get("/does-not-exist")
    assert r.status_code == 404
    assert r.get_json() == {"error": "not found"}


def test_boom_returns_500(client):
    r = client.get("/boom")
    assert r.status_code == 500


def test_metrics_exposed(client):
    client.get("/health")
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    for name in (
        "http_requests_total",
        "http_request_duration_seconds",
        "http_requests_in_progress",
        "app_info",
        "app_start_time_seconds",
        "notes_stored",
    ):
        assert name in body
