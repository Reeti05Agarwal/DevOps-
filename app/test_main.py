import pytest

from main import app, NOTES


@pytest.fixture
def client():
    NOTES.clear()
    app.config["TESTING"] = True
    return app.test_client()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_version(client):
    r = client.get("/version")
    assert r.status_code == 200
    assert "version" in r.get_json()


def test_add_and_list_notes(client):
    r = client.post("/notes", json={"text": "hello devops"})
    assert r.status_code == 201
    r = client.get("/notes")
    assert r.get_json()["notes"] == ["hello devops"]


def test_add_note_requires_text(client):
    r = client.post("/notes", json={})
    assert r.status_code == 400


def test_metrics_exposed(client):
    client.get("/health")
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "http_requests_total" in body
    assert "http_request_duration_seconds" in body
