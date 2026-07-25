# Multilingual Voice AI Support Platform

A production-grade multilingual (English / Hindi / Hinglish) Voice AI customer-support system: browser + telephone voice sessions, streaming STT/LLM/TTS, retrieval over real support docs, authenticated business tools, human handoff, call replay, and automated evaluations.

- Requirements: [requirement.md](requirement.md)
- Execution plan: [plan.md](plan.md)

## Repository layout

```
backend/   Python: FastAPI API + (soon) LiveKit agent worker
web/       Next.js voice client + ops dashboard (later phase)
evals/     Evaluation suites (later phase)
infra/     docker-compose for local dev, deploy configs
docs/      Architecture / API / security docs
```

## Local development

Prerequisites: Python 3.11+, Docker Desktop, Node 22+ (for `web/`, later).

```sh
# 1. Start local infrastructure (Postgres 16 + pgvector, Redis 7)
docker compose -f infra/docker-compose.dev.yml up -d

# 2. Backend setup (once)
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
copy .env.example .env

# 3. Apply database migrations, then seed baseline data (safe to re-run)
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m app.seed

# 4. Run the API
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Then:

- `GET http://localhost:8000/health` — liveness (process is up)
- `GET http://localhost:8000/ready` — readiness (Postgres + Redis reachable)
- `http://localhost:8000/docs` — interactive OpenAPI docs
