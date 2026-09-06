# Vote Lab backend — FastAPI (ASGI), served by uvicorn. Dev image.
FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first (better layer caching).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY . .

# Environment: development | testing | production.
ENV APP_ENV=development

# Port the FastAPI app listens on.
EXPOSE 4434

# Run as a non-root user (hardening). The app binds 4434 (> 1024) and writes
# nothing under root-owned paths, so an unprivileged user is sufficient.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

# Liveness: /api/v2/health returns 200 healthy / 503 degraded (urlopen raises on
# 503 → non-zero exit → unhealthy). Stdlib only, no curl needed.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:4434/api/v2/health')"]

# uvicorn serves the whole API (FastAPI app at api.main:app).
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "4434"]
