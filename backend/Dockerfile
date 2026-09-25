# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# libpq for psycopg, the rest for Pillow (JPEG/PNG/WEBP).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libjpeg62-turbo-dev \
        zlib1g-dev \
        libwebp-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
RUN pip install --upgrade pip && pip install -r requirements/prod.txt

COPY . .

RUN useradd --create-home --uid 1000 nogoya \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R nogoya:nogoya /app
USER nogoya

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz/ || exit 1

# Daphne (ASGI) rather than gunicorn: the project is wired for Channels.
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
