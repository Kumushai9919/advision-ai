# syntax=docker/dockerfile:1.7-labs
FROM python:3.11-slim AS app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN addgroup --system --gid 1001 app && adduser --system --uid 1001 --ingroup app app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip && \
    pip install -r requirements.txt

COPY --chown=app:app src/ ./src/

RUN mkdir -p /data && chown -R app:app /data

USER app

COPY .env.production .env

EXPOSE 8000

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "src.main:app", \
     "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60"]