# Hackathon Techtonic

Next.js + FastAPI + Postgres starter.

```bash
cp .env.example .env   # add your OPENROUTER_API_KEY for Jev categorization
docker compose up -d --build
cd frontend && pnpm install && pnpm dev
```

Open http://localhost:3000. API docs at http://localhost:8000/docs.

See [CLAUDE.md](CLAUDE.md) for project rules (pnpm only).
