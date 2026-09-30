#!/usr/bin/env sh
# Switch the Gemini (Vertex AI) service account the backend uses.
#   ./scripts/use-gcp.sh hackathon   -> secrets/gcp-sa-hackathon.json
#   ./scripts/use-gcp.sh billem      -> secrets/gcp-sa-billem.json
# Copies the key to secrets/gcp-sa.json (mounted into the backend), sets GOOGLE_CLOUD_PROJECT in .env
# from the key's project_id, recreates the backend container, and makes one test call to Gemini.
set -eu
cd "$(dirname "$0")/.."

name="${1:-}"
key="secrets/gcp-sa-${name}.json"
if [ -z "$name" ] || [ ! -f "$key" ]; then
  echo "usage: $0 <name>   (available: $(ls secrets/gcp-sa-*.json 2>/dev/null | sed 's#secrets/gcp-sa-##; s#\.json##' | tr '\n' ' '))" >&2
  exit 1
fi

project=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['project_id'])" "$key")
cp "$key" secrets/gcp-sa.json
chmod 600 secrets/gcp-sa.json
if grep -q '^GOOGLE_CLOUD_PROJECT=' .env; then
  sed -i.bak "s/^GOOGLE_CLOUD_PROJECT=.*/GOOGLE_CLOUD_PROJECT=${project}/" .env && rm -f .env.bak
else
  echo "GOOGLE_CLOUD_PROJECT=${project}" >> .env
fi
echo "Using ${key} (project ${project})"

docker compose up -d --force-recreate backend >/dev/null 2>&1
docker compose exec -T backend python - <<'PY'
import time
from app.config import settings
from app.detection import gemini
for _ in range(30):
    try:
        gemini._client()
        break
    except Exception:
        time.sleep(1)
try:
    from google.genai import types
    r = gemini._client().models.generate_content(model=settings.gemini_model, contents="Reply with the single word OK")
    print(f"Gemini OK: {settings.gemini_model} in {settings.google_cloud_location} answered {r.text.strip()!r}")
except Exception as e:
    print(f"Gemini NOT usable with this account ({settings.gemini_model}): {str(e)[:200]}")
    print("Detection will use the rule-based fallback until this is fixed.")
PY
