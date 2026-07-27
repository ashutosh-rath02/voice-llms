# Execution Plan — Multilingual Voice AI Support Platform

Companion to [requirement.md](requirement.md). This document tracks the decisions, stack, and milestone-by-milestone task breakdown. Status markers: `[ ]` todo, `[x]` done, `[~]` in progress.

---

## 1. Key Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| D1 | Voice framework | **LiveKit Agents (Python)** — proposed | Built-in WebRTC infra (LiveKit Cloud free tier), first-class SIP for Phase 4 telephony, built-in VAD/turn-detection/barge-in, provider plugins for Deepgram/ElevenLabs/Cartesia/OpenAI/Anthropic, metrics API that maps directly to the PRD §7.3 latency-tracing requirement. Pipecat is the alternative if we prefer Daily. |
| D2 | STT | **Deepgram** (streaming, partials, word timestamps) — proposed | Nova models support English + Hindi + code-switching (`multi`). Fallback/alternative for Hinglish quality: Google STT or Sarvam AI (evaluate in Phase 5). |
| D3 | LLM | **OpenAI (`gpt-4o-mini`, primary) + Groq (fast alternative)** — user decision 2026-07-25 | Both ride OpenAI-compatible APIs via LiveKit plugins; the active `agent_versions` row picks the provider, so switching (or A/B latency comparison) is a data change, not a deploy. |
| D4 | TTS | **ElevenLabs Flash v2.5** (multilingual incl. Hindi, low first-audio latency) — proposed | Cartesia Sonic is the backup; both stream and support barge-in cancellation. |
| D5 | Hosting posture | **Managed/free-tier first**: LiveKit Cloud + Neon Postgres (pgvector) + Upstash Redis + Fly.io/Railway (Python services) + Vercel (Next.js) + Cloudflare R2 (audio) — proposed | PRD §12 suggests AWS; for a portfolio project the managed stack cuts cost/ops dramatically and everything has an AWS-equivalent migration path. Revisit if AWS experience itself is a portfolio goal. |
| D6 | Telephony (Phase 4) | **Open — decide by end of Phase 3.** Twilio (easiest LiveKit SIP integration; US number, so calling it from India costs ISD) vs Exotel/Plivo (Indian numbers, more integration work) | India inbound-number regulations make this the highest-risk external dependency. Prototype with Twilio trial; validate Exotel media-streaming access early. |
| D7 | Support domain (Phase 2) | **Smart-home device support desk, using Home Assistant's public docs corpus** — decided 2026-07-26 | Real, permissively-licensed, 1500+ documents (far above the 50+ minimum), naturally support/troubleshooting-shaped. Ticketing (Phase 3) will use GitHub Issues against the same open-source project. Architecture stays domain-independent — swapping corpora is a re-run of the ingestion CLI on a different folder. |
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
- [x] Signup/login/refresh/logout/me, argon2 hashing, JWT access + refresh with single-use rotation and Redis-backed revocation, role claim, `require_roles` RBAC dependency. Verified over HTTP including failure paths.
- [x] `POST /api/v1/voice/token`: mints a room-scoped LiveKit token for the authenticated user and creates the `conversations` row. Verified incl. 401 unauthenticated.

### 3.4 Voice agent worker
- [x] LiveKit Agents worker (v1.6.7): Silero VAD → Deepgram STT → OpenAI/Groq LLM (chosen by active agent version) → ElevenLabs TTS. Registers with LiveKit Cloud (verified, India South region).
- [x] Barge-in: AgentSession interruption handling; interrupted assistant turns stored with `interrupted=true` and played-content truncation.
- [x] Turn-detection config read from `provider_configs.turn_detection.default`, not hard-coded.
- [x] Event hooks → persistence via ConversationRecorder: partials (buffered into turn.extra), final turns, state events, ad-hoc room handling.
- [x] Latency capture per turn: STT transcription delay, LLM TTFT, TTS TTFB, computed total → `turn_latency_metrics` (+ raw JSONB).
- [x] Graceful shutdown callback finalizes the conversation row.
- [ ] Live audio verification (user speaks to the agent, then inspect persisted turns/latency).

### 3.5 Web client
- [x] Next.js 16 app (TypeScript, Tailwind 4) with login; voice page joins the LiveKit room with mic, agent-state pill, mute, end-call.
- [x] Live transcript pane via room transcription events (partials at reduced opacity, replaced in place when final); agent state indicator (listening/thinking/speaking).
- [x] Reconnecting banner (LiveKit auto-reconnect) + mic-failure fallback message. CORS middleware added to API (was missing — blocked all browser calls).
- [ ] Live browser test by user.

### 3.6 Replay
- [x] `GET /conversations` + detail endpoint: turns, state history, latency per turn; customers see own, staff see all; foreign ids 404.
- [x] Replay page: transcript timeline with per-turn latency chips (total >2s highlighted), interruption badges, expandable STT partials, state timeline.

### 3.7 Staging deployment
- [x] Backend Dockerfile (single image, API + worker commands; voice models baked at build; migrations on boot) + .dockerignore.
- [x] CI (GitHub Actions): ruff + import smoke, web lint + build, docker build.
- [x] Deployment runbook: [docs/deployment.md](docs/deployment.md) — Railway (Postgres/pgvector + Redis + api + worker) + Vercel (web) + LiveKit staging project.
- [ ] User: create Railway + Vercel accounts, LiveKit staging project (see runbook §one-time setup).
- [ ] Provision services, set env vars, deploy, seed, smoke test.

### Exit criteria (from PRD)
- A real voice conversation completes end-to-end in the browser on staging.
- Interrupting the agent works and is visible in the timeline.
- The conversation is persisted and replayable with per-turn latency.

## 4. Later Phases (summary — detailed breakdown when each starts)

- **Phase 2a — RAG core (done, 2026-07-27):** `knowledge_documents`/`knowledge_chunks`/`retrieval_events` schema (pgvector HNSW cosine index + FTS GIN expression index); Jekyll/Liquid-aware markdown ingestion pipeline (heading-path-aware chunking, idempotent by content hash, protects real Jinja code examples from Jekyll-tag stripping); hybrid retrieval (vector + full-text, fused via Reciprocal Rank Fusion) with every query logged as a `RetrievalEvent`; staff-only `/knowledge/documents` + `/knowledge/search` API. **1,498 real Home Assistant integration docs indexed, 12,740 chunks, 100% embedded** (`text-embedding-3-small`) — verified against real support-style queries (MQTT, Zigbee, Z-Wave) with correct top results and dual-signal RRF fusion visibly outscoring single-signal matches.
- **Phase 2b — agent integration (done, 2026-07-27):** `search_knowledge_base` function tool wired into the agent via `AgentSession[SessionData]` (RunContext-injected DB session factory, OpenAI client, conversation_id — logic split into `run_knowledge_search` so it's testable without a live room). New `agent_versions` row `v0.2.0` (grounding/escalation system prompt: search before answering setup/config/troubleshooting questions, admit when nothing relevant was found, offer human escalation instead of guessing) promoted to ACTIVE, `v0.1.0` demoted to INACTIVE — `status` is the one mutable field on an otherwise-immutable version row. Retrieval evidence surfaced in the replay view (query, matched docs with real source links, vector/FTS rank badges). **Verified two ways:** (1) direct LLM test against the real OpenAI API — correctly called the tool for a real troubleshooting question, correctly declined and stayed in-persona for an off-topic one; (2) live end-to-end voice call — agent handled an STT mis-transcription, took a self-correction from the user, searched twice, and gave a correct grounded answer (real MQTT/Mosquitto docs) with both lookups logged and visible in replay.
- **Phase 2 retrieval-specific eval cases:** deferred to Phase 6 (automated evaluation suites), where they belong with the rest of the eval harness.
- **Phase 3 — Business tools:** customers/products schema + APIs, tool gateway with idempotency keys + confirmation policy enforcement, ticketing (GitHub Issues or Linear), scheduling (Cal.com or Google Calendar), messaging (Resend email first; WhatsApp/SMS optional).
- **Phase 4 — Telephony:** provider per D6, LiveKit SIP trunk, inbound number, recording w/ consent line, webhooks, DTMF, human transfer to a real number, phone-based identity lookup.
- **Phase 5 — Multilingual:** Hindi/Hinglish tuning, per-turn language detection, identifier read-back rules, language switching mid-call, STT provider comparison (Deepgram vs Google vs Sarvam) with eval data.
- **Phase 6 — Evals & observability:** simulated-caller suites (text + prerecorded audio), tool/retrieval/latency/confirmation assertions, failure injection, regression comparison across agent versions, release gating, dashboards.
- **Phase 7 — Hardening:** timeouts/retries/circuit breakers, provider fallback, PII masking, retention/deletion workflows, cost tracking, load tests, security review.

## 5. Immediate Next Steps

1. Confirm decisions D1–D5, D8 (or adjust).
2. Create provider accounts + API keys: LiveKit Cloud, Deepgram, Anthropic, ElevenLabs.
3. Start §3.1 scaffolding.
