FROM ubuntu:latest
LABEL authors="ogahserge"

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev geos-bin gdal-bin postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /app

# Requirements
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# App code
COPY . /app

# Collect static at build (optionnel si tu as du static)
RUN mkdir -p /app/staticfiles /app/media

# User (optionnel)
# RUN useradd -m appuser && chown -R appuser:appuser /app
# USER appuser

# Gunicorn (ASGI) -> sigh.asgi:application
ENV DJANGO_SETTINGS_MODULE=sigh.settings.prod \
    PORT=8000

EXPOSE 8000

CMD ["gunicorn", "sigh.asgi:application", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "4", "--bind", "0.0.0.0:8000", \
     "--timeout", "120", "--graceful-timeout", "30"]


