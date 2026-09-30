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
docker compose up -d --build   # Postgres on :5432, FastAPI on :8000 (hot reload)
cd frontend && pnpm install && pnpm dev   # Next.js on :3000
```
- API docs: http://localhost:8000/docs
- DB connection: `postgresql://app:app@localhost:5432/app`
- Frontend reads the API base URL from `NEXT_PUBLIC_API_URL` (`frontend/.env.local`).

## Backend conventions
- Python deps go in `backend/requirements.txt`; rebuild with `docker compose up -d --build backend`.
- Models in `app/models.py`, Pydantic schemas in `app/schemas.py`, routes in `app/main.py`.
- Schema changes go through Alembic (`backend/migrations/`); migrations run automatically on container start.
  - New migration: `docker compose exec backend alembic revision --autogenerate -m "<message>"`, then review the generated file.

## Jev categorization
- Items are sorted into categories by Jev (`~typesafe/jev-latest`) through OpenRouter's Decisions API (`app/jev.py`).
- Categories and their descriptions live in `app/categories.py`; edit them there.
- Needs `OPENROUTER_API_KEY` in the root `.env` (copy `.env.example`). Without it, items are saved with no category.
- Jev failures never block saving an item; `POST /items/{id}/categorize` re-runs it.

## Git
- Do not add `Co-Authored-By`, "Generated with Claude Code", session links, or any other AI attribution to commit messages or PR descriptions.
- Never commit or push directly to `main`. Do all work on a feature branch, push it, and open a pull request into `main`.
- Open PRs with the GitHub MCP server (official `github/github-mcp-server`). If it isn't installed, install it first.

## Tools and integrations
- This is a personal project. Do not use anything from Conveo: no Conveo MCP servers (e.g. `Conveo - Github`, `Conveo - BigQuery`), no `conveo-*` plugins or skills, no Conveo accounts, repos, or org resources.
- Use only project-local or personal tooling (e.g. the MCP servers in `.mcp.json`).
