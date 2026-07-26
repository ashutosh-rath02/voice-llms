# Deployment (staging)

Target topology — three managed platforms, all with free/hobby tiers:

| Piece | Where | Why |
|---|---|---|
| Postgres (pgvector) + Redis | Railway plugins | One dashboard next to the services that use them |
| API (FastAPI) | Railway service #1 | Runs `backend/Dockerfile` default CMD (migrations, then uvicorn) |
| Agent worker | Railway service #2 | Same image, command `python -m app.agent.worker start` |
| Web (Next.js) | Vercel | Native Next.js hosting; free SSL, preview deploys |
| Realtime media | LiveKit Cloud | Already provisioned (dev project) — create a second project for staging |

## One-time account setup (human steps)

1. **Railway** — sign up at https://railway.app (GitHub login). Install CLI: `npm i -g @railway/cli`, then `railway login --browserless` and follow the printed link.
2. **Vercel** — sign up at https://vercel.com (GitHub login). Easiest path: dashboard → *Add New Project* → import `ashutosh-rath02/voice-llms`, set **Root Directory = `web`**.
3. **LiveKit Cloud** — create a second project named `voiceai-staging` (keys must differ from dev).

## Railway configuration

Create one Railway project ("voiceai-staging") containing:

1. **Postgres** — add the *pgvector* template (plain Postgres lacks the extension).
2. **Redis** — add the Redis plugin.
3. **api** service — *Deploy from GitHub repo*, root `backend/`. Railway auto-detects the Dockerfile.
4. **worker** service — same repo/root; override **Start Command**: `python -m app.agent.worker start`.

### Environment variables (both api and worker)

```
APP_ENV=staging
LOG_LEVEL=INFO
DATABASE_URL=<Railway Postgres URL, swap scheme to postgresql+asyncpg://>
REDIS_URL=<Railway Redis URL>
JWT_SECRET=<generate: openssl rand -hex 32>
SEED_ADMIN_EMAIL=<real admin email>
SEED_ADMIN_PASSWORD=<generated strong password>
CORS_ORIGINS=https://<your-app>.vercel.app
LIVEKIT_URL=wss://voiceai-staging-xxxx.livekit.cloud
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
DEEPGRAM_API_KEY=...
OPENAI_API_KEY=...
GROQ_API_KEY=...
ELEVENLABS_API_KEY=...
```

Notes:
- The API runs `alembic upgrade head` on boot (see Dockerfile CMD); seed once via
  `railway run --service api python -m app.seed`.
- Health check path for the api service: `/ready`.

## Vercel configuration

- Root directory: `web`
- Env var: `NEXT_PUBLIC_API_URL=https://<railway-api-domain>`
- Every push to `main` auto-deploys; PRs get preview URLs.

## Post-deploy smoke test

```sh
curl https://<api>/health          # {"status":"ok"}
curl https://<api>/ready           # postgres + redis ok
# login, mint a voice token, confirm a conversation row appears
```

Then open the Vercel URL, sign in, run one voice call end-to-end, and confirm
the conversation shows in the replay list with latency chips.

## Rollback

- API/worker: Railway → service → Deployments → redeploy any previous build.
- Web: Vercel → Deployments → promote a previous deployment.
- Database: migrations are additive so far; `alembic downgrade -1` if ever needed.
