# Vote Lab backend — FastAPI (ASGI), served by uvicorn. Dev image.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
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

# uvicorn serves the whole API (FastAPI app at api.main:app).
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "4434"]
