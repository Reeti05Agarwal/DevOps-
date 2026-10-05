"""Tiny notes service used for the DevOps CA-2 assignment.

Endpoints
  GET  /health   -> liveness probe (used by Docker/K8s/Prometheus)
  GET  /version  -> app version (changes between rolling-update demos)
  GET  /notes    -> list notes
  POST /notes    -> add a note  {"text": "..."}
  GET  /metrics  -> Prometheus metrics (requests, latency, errors)
"""
import os
import time

from flask import Flask, jsonify, request, g
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")

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
)


@app.before_request
def _start_timer():
    g.start = time.perf_counter()


@app.after_request
def _record_metrics(response):
    endpoint = request.url_rule.rule if request.url_rule else "unmatched"
    if endpoint != "/metrics":
        REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
        REQUEST_LATENCY.labels(endpoint).observe(time.perf_counter() - g.start)
    return response


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/version")
def version():
    return jsonify(version=APP_VERSION)


@app.get("/notes")
def list_notes():
    return jsonify(notes=NOTES)


@app.post("/notes")
def add_note():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()
    if not text:
        return jsonify(error="text is required"), 400
    NOTES.append(text)
    return jsonify(added=text, count=len(NOTES)), 201


@app.get("/boom")
def boom():
    """Deliberate 500 so the Grafana error-rate panel has something to show."""
    return jsonify(error="intentional failure"), 500


@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
