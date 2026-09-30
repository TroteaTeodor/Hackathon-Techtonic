# Project rules

## Stack
- `frontend/` — Next.js (App Router, TypeScript, Tailwind)
- `backend/` — FastAPI + SQLAlchemy 2 (psycopg 3)
- Postgres — runs in Docker via `docker-compose.yml`, alongside the backend

## Package manager: pnpm only
- **Always use `pnpm`. Never use `npm`, `npx`, or `yarn`.**
  - Install: `pnpm install` / `pnpm add <pkg>` / `pnpm add -D <pkg>`
  - Run scripts: `pnpm dev`, `pnpm build`, `pnpm lint`
  - One-off binaries: `pnpm dlx <pkg>` (instead of `npx`)
- Never commit `package-lock.json` or `yarn.lock`; only `pnpm-lock.yaml`.

## Running locally
```bash
cp .env.example .env            # then fill in GOOGLE_CLOUD_PROJECT, SESSION_SECRET, DEMO_PASSWORD
# put the GCP service-account key at secrets/gcp-sa.json (git-ignored)
./scripts/dev.sh               # API (migrate + auto-seed if empty) and frontend; --reset wipes the DB first
# or by hand: docker compose up -d --build && cd frontend && pnpm install && pnpm dev
```
- API docs: http://localhost:8000/docs · health: http://localhost:8000/health (`"ai": true` when Gemini is configured)
- Postgres isn't published to the host. Open a shell with `docker compose exec db psql -U app -d app`. The backend listens
  on 127.0.0.1:8000 only. Fresh start: `docker compose down -v`
  (also needed after changing `POSTGRES_PASSWORD`, because Postgres only sets it when the volume is created).
- Frontend reads `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_USE_MOCKS` from `frontend/.env.local`.
- Demo logins (password = `DEMO_PASSWORD`): `advisor`, and customers `sara` (moving home), `lien` (baby),
  `ahmed` (new job, no marketing consent), `marc` (retirement), `julie` (financial stress), `pieter` (car), `jan` (routine).

### Gemini service account
- Gemini is called only through Vertex AI with a service-account key (no API keys).
- Keys live in `secrets/gcp-sa-<name>.json` (git-ignored). Switch with `./scripts/use-gcp.sh <name>`: it copies the key
  to `secrets/gcp-sa.json`, sets `GOOGLE_CLOUD_PROJECT` in `.env`, recreates the backend and makes one test call.
  - `hackathon`: `qwiklabs-gcp-02-7084aced4e5c`, the organizers' project. Its `vertexai.allowedModels` org policy
    currently denies every model, so detection falls back to rules until the organizers allow Gemini.
  - `billem`: `billem-499113`, a working fallback with Gemini 3.8 Flash.

### Environment variables (root `.env`, see `.env.example`)
| Variable | Purpose |
|---|---|
| `POSTGRES_PASSWORD` | Local Postgres password; docker-compose refuses to start without it. |
| `SESSION_SECRET` | Signs session cookies. Required, ≥32 chars; the backend refuses to start without it. |
| `DEMO_PASSWORD` | Password for all demo accounts. Without it no demo users are created. |
| `COOKIE_SECURE` | `true` only when served over HTTPS. |
| `GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | Gemini via Vertex AI with the service-account key mounted from `secrets/gcp-sa.json` (location `global` for Gemini 3.x). This is the only way Gemini is called: API keys are disabled on the hackathon projects. |
| `DETECTOR` | `cascade` (default: Jev first, Gemini when Jev is unsure), `jev`, `gemini` or `rules`. See design.md decision 1. |
| `JEV_ESCALATION_THRESHOLD` | Jev confidence below which Gemini decides (default `0.75`). |
| `OPENROUTER_API_KEY` | Jev (OpenRouter Decisions API), the first step of detection. |
| `GEMINI_MODEL` | Default `gemini-3.8-flash`, with `GEMINI_THINKING_LEVEL=low`. |

## Backend
- Python deps in `backend/requirements.txt`; rebuild with `docker compose up -d --build backend`.
- Tests: `docker compose exec backend pytest -q` (separate `app_test` database, rules only, no AI calls).
  `tests/test_contract.py` validates `frontend/src/mocks/*.json` against the Pydantic contract.
- Evals (A/B of rules vs Jev vs Gemini variants, calibration, cost, guardrail invariants, McNemar tests):
  `docker compose exec -e OPENROUTER_API_KEY backend python -m evals.run` (about 15 min, around 1,400 model calls).
  It writes `backend/evals/REPORT.md`; raw results in `backend/evals/results/` are git-ignored.
  Validate new hard cases with `python -m evals.check_cases evals/hard_cases.json`. Production Gemini settings
  (`GEMINI_THINKING_LEVEL=low`) were chosen from the report; see design.md decision 1b.
- Schema changes go through Alembic (`backend/migrations/`); migrations run on container start.
  New migration: `docker compose exec backend alembic revision --autogenerate -m "<message>"`, then review it.
- Layout (`backend/app/`):
  - `schemas.py`: the API contract (mirrors `frontend/src/lib/types.ts`; change both together)
  - `models.py`: tables · `seed.py`: synthetic story customers + generated population
  - `detection/`: `__init__.py` has the cascade: `jev.py` first, `gemini.py` when Jev is unsure (<75%), and `rules.py` as the safety net
  - `twin.py`: 12-month forecast · `interventions.py`: catalog + ordered guardrail policy
  - `analysis.py`: detect → twin → policy, persisted; runs only on new signal, preference change or moment rejection
  - `auth.py`: scrypt hashes, JWT session cookie, login rate limit, `require_customer` / `require_advisor`
  - `routers/`: `auth.py` (`/auth/*`), `me.py` (`/me/*`, customer from session only), `advisor.py`
- Security rules: customer routes never take a customer ID; lookups filter by the session's customer and
  return 404 for anything else. Every advisor route depends on `require_advisor`.

## Git
- Do not add `Co-Authored-By`, "Generated with Claude Code", session links, or any other AI attribution to commit messages or PR descriptions.
- Never commit or push directly to `main`. Do all work on a feature branch, push it, and open a pull request into `main`.
- Open PRs with the GitHub MCP server (official `github/github-mcp-server`). If it isn't installed, install it first.
  - It is configured in `.mcp.json` and needs `GITHUB_PERSONAL_ACCESS_TOKEN` exported in your shell (e.g. `export GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token)` or a fine-grained PAT).

## Tools and integrations
- This is a personal project. Do not use anything from Conveo: no Conveo MCP servers (e.g. `Conveo - Github`, `Conveo - BigQuery`), no `conveo-*` plugins or skills, no Conveo accounts, repos, or org resources.
- Use only project-local or personal tooling (e.g. the MCP servers in `.mcp.json`).

## Specs (OpenSpec)
- Plans live in `openspec/changes/<change>/` (proposal, specs, design, tasks). The active change is `kbc-foresight`.
- Implement with `/opsx:apply`, and tick tasks in `tasks.md` as they're done.
- **When a change is completed** (all tasks ticked and merged into `main`), archive it right away with `/opsx:archive` (`openspec archive <change>`). That moves it into `openspec/changes/archive/` and merges its specs into `openspec/specs/`. Archive on a branch and merge via a PR like any other change.
