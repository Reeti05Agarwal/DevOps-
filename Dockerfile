# ---- Stage 1: build wheels so the runtime image has no compilers or pip cache ----
FROM python:3.12-slim AS builder
WORKDIR /build
COPY app/requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ---- Stage 2: small runtime image ----
FROM python:3.12-slim

ARG APP_VERSION=1.0.0
LABEL org.opencontainers.image.title="notes-service" \
      org.opencontainers.image.description="DevOps CA-2 notes service" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_VERSION=${APP_VERSION}

WORKDIR /srv
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY app/main.py .

# Run as a fixed non-root UID so Kubernetes runAsNonRoot can verify it
RUN useradd --uid 10001 --no-create-home appuser
USER 10001

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# One worker + threads: prometheus_client keeps metrics per process, so several
# workers would each report different counters and the dashboard would jump around.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "main:app"]
