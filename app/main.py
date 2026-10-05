"""Tiny notes service used for the DevOps CA-2 assignment.

Endpoints
  GET    /health      -> liveness probe (process is up)
  GET    /ready       -> readiness probe (app can serve traffic)
  GET    /version     -> app version (changes between rolling-update demos)
  GET    /notes       -> list notes
  POST   /notes       -> add a note  {"text": "..."}
  DELETE /notes/<id>  -> delete a note by index
  GET    /metrics     -> Prometheus metrics (requests, latency, errors, uptime)
  GET    /boom        -> deliberate 500 for the error-rate panel
  GET    /slow        -> deliberate slow response for the latency panel
"""
import json
import logging
import os
import random
import sys
import time
import uuid

from flask import Flask, g, jsonify, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")
MAX_NOTE_LENGTH = int(os.environ.get("MAX_NOTE_LENGTH", "500"))
# Set FAIL_READINESS=true to build a deliberately broken release for the rollback demo.
FAIL_READINESS = os.environ.get("FAIL_READINESS", "false").lower() == "true"
START_TIME = time.time()


class JsonFormatter(logging.Formatter):
    """One JSON object per line, so logs are easy to grep and ship to Loki/ELK."""

    def format(self, record):
        entry = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "msg": record.getMessage(),
            "version": APP_VERSION,
        }
        entry.update(getattr(record, "extra_fields", {}))
        return json.dumps(entry)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
log = logging.getLogger("notes-service")
log.addHandler(handler)
log.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
log.propagate = False

app = Flask(__name__)
NOTES = []

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
IN_PROGRESS = Gauge("http_requests_in_progress", "Requests currently being served")
NOTES_TOTAL = Gauge("notes_stored", "Number of notes currently stored")
APP_INFO = Gauge("app_info", "Application build info", ["version"])
APP_INFO.labels(APP_VERSION).set(1)
Gauge("app_start_time_seconds", "Unix time the app started").set(START_TIME)


@app.before_request
def _start_timer():
    g.start = time.perf_counter()
    g.request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
    IN_PROGRESS.inc()


@app.after_request
def _record_metrics(response):
    IN_PROGRESS.dec()
    endpoint = request.url_rule.rule if request.url_rule else "unmatched"
    duration = time.perf_counter() - g.start
    response.headers["X-Request-ID"] = g.request_id
    response.headers["X-App-Version"] = APP_VERSION
    if endpoint != "/metrics":
        REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
        REQUEST_LATENCY.labels(endpoint).observe(duration)
        log.info(
            "request",
            extra={
                "extra_fields": {
                    "request_id": g.request_id,
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                }
            },
        )
    return response


@app.get("/")
def index():
    return jsonify(
        service="notes-service",
        version=APP_VERSION,
        endpoints=["/health", "/ready", "/version", "/notes", "/metrics"],
    )


@app.get("/health")
def health():
    return jsonify(status="ok", uptime_seconds=round(time.time() - START_TIME, 1))


@app.get("/ready")
def ready():
    if FAIL_READINESS:
        return jsonify(status="not ready"), 503
    return jsonify(status="ready")


@app.get("/version")
def version():
    return jsonify(version=APP_VERSION)


@app.get("/notes")
def list_notes():
    return jsonify(notes=NOTES, count=len(NOTES))


@app.post("/notes")
def add_note():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    if not text:
        return jsonify(error="text is required"), 400
    if len(text) > MAX_NOTE_LENGTH:
        return jsonify(error=f"text must be at most {MAX_NOTE_LENGTH} characters"), 400
    NOTES.append(text)
    NOTES_TOTAL.set(len(NOTES))
    return jsonify(id=len(NOTES) - 1, added=text, count=len(NOTES)), 201


@app.delete("/notes/<int:note_id>")
def delete_note(note_id):
    if note_id < 0 or note_id >= len(NOTES):
        return jsonify(error="note not found"), 404
    removed = NOTES.pop(note_id)
    NOTES_TOTAL.set(len(NOTES))
    return jsonify(deleted=removed, count=len(NOTES))


@app.get("/boom")
def boom():
    """Deliberate 500 so the Grafana error-rate panel has something to show."""
    log.error("intentional failure triggered", extra={"extra_fields": {"request_id": g.request_id}})
    return jsonify(error="intentional failure"), 500


@app.get("/slow")
def slow():
    """Deliberate 0.2-1.0s delay so the latency panel shows a spread."""
    time.sleep(random.uniform(0.2, 1.0))
    return jsonify(status="slow but ok")


@app.errorhandler(404)
def not_found(_):
    return jsonify(error="not found"), 404


@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
