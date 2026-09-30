# Aikido security audit

Screenshots from the Aikido scan of `main`, kept for the submission (before and after).

| # | Screenshot | What it shows |
|---|---|---|
| 1 | [01-before-3-issues.png](01-before-3-issues.png) | **Before:** the first scan found 3 issues: a container running as root, uncontrolled resource consumption, and hard-coded credentials |
| 2 | [02-rescan-5-issues.png](02-rescan-5-issues.png) | A rescan after new code landed: 5 issues, adding possible file inclusion and `assert` use in the eval tooling |
| 3 | [03-compliance-before.png](03-compliance-before.png) | Compliance checks: SAST and IaC non-compliant |
| 4 | [04-after-0-issues.png](04-after-0-issues.png) | **After:** 0 issues, 23 solved |

## What we fixed

| Finding | Fix |
|---|---|
| Docker container runs as default root user | `backend/Dockerfile` runs as an unprivileged `app` user (uid 1000) |
| Hard-coded credentials (`docker-compose.yml`) | The Postgres password comes from `POSTGRES_PASSWORD` in the git-ignored `.env`; no default credentials in code; Postgres is no longer published to the host; the backend listens on 127.0.0.1 only |
| Uncontrolled resource consumption (`backend/app/main.py`) | 64 KB request-body limit (413), per-client write rate limit (429), bounded validation-error responses, a paginated customer list (max 1000), capped concurrent scrypt checks (503), and a per-customer signal limit (409) |
| Potential file inclusion (`evals/check_cases.py`) | The eval tools only read `.json` files inside `backend/evals/` |
| Dangerous use of `assert` | Replaced with explicit checks in app and eval code |

The fixes are in commits `2309807` and `4625b4a` on `main`. The tests that cover them are in `backend/tests/test_api.py` and `backend/tests/test_detection.py`.
