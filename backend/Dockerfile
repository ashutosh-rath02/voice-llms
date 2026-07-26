# One image, two processes: the deploy platform runs it twice with different
# commands —
#   API:    (default CMD)
#   Worker: python -m app.agent.worker start
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dependency layer first so code edits don't re-install everything.
COPY pyproject.toml ./
RUN pip install .

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
# The pyproject copy above installed deps from a bare project; reinstall the
# package itself now that source is present (fast — deps are cached).
RUN pip install --no-deps .

# Bake voice-model assets (Silero VAD weights, turn detector, etc.) into the
# image so they are not downloaded on every cold start.
RUN python -m app.agent.worker download-files

EXPOSE 8000
# ${PORT} is injected by the platform (Railway/Fly); default for local runs.
# Migrations run before the API starts — single-instance staging, safe.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
