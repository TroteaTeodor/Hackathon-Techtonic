#!/usr/bin/env sh
# One command for local development:
#   ./scripts/dev.sh           start Postgres + API (migrates and auto-seeds an empty database), then the frontend
#   ./scripts/dev.sh --reset   wipe the database first, so it is re-seeded from scratch
set -eu
cd "$(dirname "$0")/.."

[ -f .env ] || { echo "No .env yet: cp .env.example .env and fill it in (see README → Run it)." >&2; exit 1; }

if [ "${1:-}" = "--reset" ]; then
  echo "Resetting the database…"
  docker compose down -v
fi

echo "Starting Postgres and the API (migrations + auto-seed run on start)…"
docker compose up -d --build

printf "Waiting for the API"
i=0
until curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -gt 90 ]; then
    echo; echo "The API didn't come up. Logs:"; docker compose logs --tail 40 backend; exit 1
  fi
  printf "."; sleep 2
done
echo " up."
docker compose logs backend 2>/dev/null | grep -E "Seed|Seeded|already seeded" | tail -3 || true

[ -f frontend/.env.local ] || printf 'NEXT_PUBLIC_API_URL=http://localhost:8000\nNEXT_PUBLIC_USE_MOCKS=false\n' > frontend/.env.local
cd frontend
pnpm install
echo "Frontend on http://localhost:3000 (API docs: http://localhost:8000/docs)"
exec pnpm dev
