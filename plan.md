# Execution Plan — Multilingual Voice AI Support Platform

Companion to [requirement.md](requirement.md). This document tracks the decisions, stack, and milestone-by-milestone task breakdown. Status markers: `[ ]` todo, `[x]` done, `[~]` in progress.

---

## 1. Key Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D1 | Voice framework | **LiveKit Agents (Python)** — proposed | Built-in WebRTC infra (LiveKit Cloud free tier), first-class SIP for Phase 4 telephony, built-in VAD/turn-detection/barge-in, provider plugins for Deepgram/ElevenLabs/Cartesia/OpenAI/Anthropic, metrics API that maps directly to the PRD §7.3 latency-tracing requirement. Pipecat is the alternative if we prefer Daily. |
| D2 | STT | **Deepgram** (streaming, partials, word timestamps) — proposed | Nova models support English + Hindi + code-switching (`multi`). Fallback/alternative for Hinglish quality: Google STT or Sarvam AI (evaluate in Phase 5). |
| D3 | LLM | **Anthropic Claude** (Sonnet to start; measure latency, consider Haiku for the realtime path) — proposed | Strong tool-use reliability for confirmation-gated actions. Any tool-capable model is swappable behind the orchestrator interface. |
| D4 | TTS | **ElevenLabs Flash v2.5** (multilingual incl. Hindi, low first-audio latency) — proposed | Cartesia Sonic is the backup; both stream and support barge-in cancellation. |
| D5 | Hosting posture | **Managed/free-tier first**: LiveKit Cloud + Neon Postgres (pgvector) + Upstash Redis + Fly.io/Railway (Python services) + Vercel (Next.js) + Cloudflare R2 (audio) — proposed | PRD §12 suggests AWS; for a portfolio project the managed stack cuts cost/ops dramatically and everything has an AWS-equivalent migration path. Revisit if AWS experience itself is a portfolio goal. |
| D6 | Telephony (Phase 4) | **Open — decide by end of Phase 3.** Twilio (easiest LiveKit SIP integration; US number, so calling it from India costs ISD) vs Exotel/Plivo (Indian numbers, more integration work) | India inbound-number regulations make this the highest-risk external dependency. Prototype with Twilio trial; validate Exotel media-streaming access early. |
| D7 | Support domain (Phase 2) | **Open — decide by end of Phase 1.** Leading option: support desk for a real open-source project (50+ real docs available, GitHub Issues = real ticketing) vs. user-owned/created business content | PRD requires 50+ real documents and real ticket creation; open-source route satisfies both with zero permission issues. |
| D8 | Auth | **FastAPI-native JWT auth** (users table, roles, refresh tokens) — proposed | PRD §14 requires login/logout/refresh/roles; owning it is simple and shows the skill. Clerk/Auth.js would be faster but hides the RBAC story. |

## 2. Repository Layout (monorepo)

```
voice-llms/
  backend/            # Python: FastAPI app + LiveKit agent worker (one package, two entrypoints)
    app/
      api/            # REST routes (auth, conversations, calls, knowledge, evals)
      agent/          # LiveKit Agents worker: pipeline, event hooks, persistence
      core/           # settings, security, db session, logging
      models/         # SQLAlchemy models
      services/       # business logic, tool gateway (Phase 3)
      workers/        # background jobs (ingestion, post-call processing)
    alembic/          # migrations
    tests/
  web/                # Next.js (TypeScript): voice client now, ops dashboard later
  evals/              # simulated-caller suites, audio corpus, assertions
  infra/              # docker-compose.dev.yml, deploy configs, CI
  docs/               # architecture, API, security, evaluation reports
  requirement.md
  plan.md
```

## 3. Milestone 1 — Real Browser Voice Session (PRD §20 / Phase 1)

Goal: an authenticated user opens the web app, talks to the agent (streaming STT → LLM → TTS) with working barge-in; the full conversation, per-turn latency trace, and state history are persisted and replayable; deployed to a staging environment.

### 3.1 Foundations
- [x] Init git repo, monorepo scaffold, `README.md`.
- [x] `docker-compose.dev.yml`: Postgres 16 + pgvector, Redis.
- [x] Backend skeleton: FastAPI, settings via env (pydantic-settings), structured logging, `/health` + `/ready` (verified: 503 + recovery when Redis stopped).
- [x] Alembic wired up (async env.py, initial migration applied).
- [ ] CI (GitHub Actions): lint (ruff), type-check (mypy/pyright), tests.

### 3.2 Data layer (Milestone-1 subset of PRD §13)
- [x] Tables: `users`, `roles`, `conversations`, `conversation_turns`, `agent_state_events`, `turn_latency_metrics`, `agent_versions`, `provider_configs`.
- [x] Audit columns (created/updated), UUID PKs, soft-delete flags where applicable.
- [x] Seed script (idempotent): roles, `v0.1.0` agent version, default turn-detection config. Dev login user moves to the auth chunk (needs password hashing).

### 3.3 Auth
- [ ] Signup/login/refresh/logout, bcrypt/argon2, JWT access + refresh, role claim.
- [ ] `POST /api/v1/voice/token`: mints a LiveKit room token for the authenticated user and creates the `conversations` row.

### 3.4 Voice agent worker
- [ ] LiveKit Agents worker: Silero VAD → Deepgram STT → Claude → ElevenLabs TTS.
- [ ] Barge-in: interruption enabled; on interrupt, cancel TTS, record interruption event, truncate assistant turn to what was actually spoken.
- [ ] Turn-detection config: endpointing delay, min speech duration, max silence — all in `provider_configs`, not hard-coded.
- [ ] Event hooks → persistence: partial/final transcripts, turn records, state events (GREETING → … minimal set for M1), errors.
- [ ] Latency capture per turn from agent metrics: STT first-partial/final, LLM TTFT, TTS TTFB, total response latency → `turn_latency_metrics`.
- [ ] Graceful shutdown: session end persists final state + summary row.

### 3.5 Web client
- [ ] Next.js app with login; voice page: mic permission, join LiveKit room, connection status, mute, end session.
- [ ] Live transcript pane (partials render then finalize), speaking indicators for both parties.
- [ ] Reconnect handling + fallback message when unrecoverable.

### 3.6 Replay
- [ ] `GET /conversations` + detail endpoint: turns, state history, latency per turn.
- [ ] Replay page: transcript timeline with per-turn latency chips and interruption markers.

### 3.7 Staging deployment
- [ ] LiveKit Cloud project; Neon Postgres; deploy backend (API + agent worker) to Fly.io/Railway; web to Vercel.
- [ ] Secrets via platform env stores; HTTPS/WSS everywhere.
- [ ] Smoke test: scripted text-mode session against the deployed agent (seed of the Phase 6 eval harness).

### Exit criteria (from PRD)
- A real voice conversation completes end-to-end in the browser on staging.
- Interrupting the agent works and is visible in the timeline.
- The conversation is persisted and replayable with per-turn latency.

## 4. Later Phases (summary — detailed breakdown when each starts)

- **Phase 2 — RAG:** ingestion pipeline (extract → chunk → embed → pgvector), hybrid retrieval + rerank, retrieval logging, evidence in replay view, groundedness guardrail, 50+ real docs from the chosen domain (D7).
- **Phase 3 — Business tools:** customers/products schema + APIs, tool gateway with idempotency keys + confirmation policy enforcement, ticketing (GitHub Issues or Linear), scheduling (Cal.com or Google Calendar), messaging (Resend email first; WhatsApp/SMS optional).
- **Phase 4 — Telephony:** provider per D6, LiveKit SIP trunk, inbound number, recording w/ consent line, webhooks, DTMF, human transfer to a real number, phone-based identity lookup.
- **Phase 5 — Multilingual:** Hindi/Hinglish tuning, per-turn language detection, identifier read-back rules, language switching mid-call, STT provider comparison (Deepgram vs Google vs Sarvam) with eval data.
- **Phase 6 — Evals & observability:** simulated-caller suites (text + prerecorded audio), tool/retrieval/latency/confirmation assertions, failure injection, regression comparison across agent versions, release gating, dashboards.
- **Phase 7 — Hardening:** timeouts/retries/circuit breakers, provider fallback, PII masking, retention/deletion workflows, cost tracking, load tests, security review.

## 5. Immediate Next Steps

1. Confirm decisions D1–D5, D8 (or adjust).
2. Create provider accounts + API keys: LiveKit Cloud, Deepgram, Anthropic, ElevenLabs.
3. Start §3.1 scaffolding.
