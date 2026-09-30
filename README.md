# KBC Foresight

**Tectonic Hackathon: KBC track.** A proof of concept for how a bank can understand what each customer needs and help at exactly the right moment, for 2.3 million customers at once.

> A life moment isn't just a sales trigger: it rewrites a customer's financial future.
> Foresight spots the moment, projects what it will do to the next 12 months, and helps **before** the pinch.

## The idea

| Step | What happens | How |
|---|---|---|
| **1. Signals** | Transactions, app events, searches and contacts with the bank | Synthetic data: 7 scripted story customers and 200 generated ones |
| **2. Understand** | Which life moment is this customer in? Moving home, a baby, a new job, retirement, buying a car, travelling abroad, financial stress, or nothing special | **Gemini 3.8 Flash** (Vertex AI, structured output) returns a probability for every moment, plus a stress score and receptiveness. A rule-based fallback keeps it working without AI. |
| **3. Foresee** | A **financial twin**: a 12-month cash-flow forecast | Deterministic arithmetic (no AI, so every number is explainable): recurring and yearly payments, plus what the detected moment adds (notary fees, a mortgage, childcare…), with **pinch points** where the balance drops below €250 |
| **4. Act** | The right help across banking, insurance and investing | An intervention catalog and an ordered **guardrail policy** (below). Pinch-point warnings go out 21 days before the month. |
| **5. Explain** | Every card carries a "Why am I seeing this?" | The reasons name the signals, the probability and the rule that applied |

**Guardrails**, applied in order:
1. A customer in financial difficulty gets **support, never sales**, routed to an advisor.
2. No marketing without consent.
3. "Not the right time" holds offers.
4. The customer's proactivity setting (minimal, balanced or proactive) sets the confidence needed.
5. Uncertain cases (50–75% confidence) go to an advisor.
6. Everything else is sent automatically.

When a customer says "Not right", that moment is never assigned to them again.

**Scale:** only customers with new signals are re-analysed, and the twin is cheap arithmetic. The advisor console's scale view shows the share handled automatically and projects the cost to 2.3M customers.

## Does it work? Evals

We A/B-tested moment detection on **340 labelled cases**:
- the 7 story customers
- the 200 generated customers
- **133 hard cases**: keyword traps (a notary for an inheritance, a gift for someone else's baby) and moments described without any obvious keyword (adoption fees, movers plus a rental guarantee, an eSIM for Norway)

Full report: [`backend/evals/REPORT.md`](backend/evals/REPORT.md).

| Detector | Accuracy | Hard cases | Calibration error | p95 latency | Cost / 1k analyses* |
|---|---|---|---|---|---|
| Keyword rules | 61.8% | 2.3% | 0.172 | — | €0 |
| Jev (OpenRouter Decisions API) | 94.1% | 96.2% | **0.023** | **0.5 s** | **€0.10** |
| **Gemini 3.8 Flash, low thinking (used)** | **96.5%** | **98.5%** | 0.060 | 9.9 s | €1.14 |
| Gemini 3.8 Flash, default thinking | 95.9% | 96.2% | 0.073 | 16.5 s | €1.99 |
| Jev first, Gemini when unsure (simulated) | 96.5% | 98.5% | — | 4.0 s | €0.23 |

- Every AI detector beats the rules by a wide margin (exact McNemar test, p < 10⁻²¹).
- The guardrails held for every detector: **0** customers in financial stress and **0** customers without consent got a sales offer.

\* Gemini costs use placeholder token prices (`PRICE_PER_MILLION_*` in `.env`). Jev reports its real cost.

## Security

The code was audited with **Aikido**. It went from 3 issues to **0 issues, 23 solved** ([before and after screenshots](docs/aikido/README.md)), and every finding was fixed:
- the container runs as a non-root user
- no hard-coded credentials
- a request-body limit and a rate limit on write requests
- no `assert`-based checks
- the tooling only reads files from its own folder

Built in from the start:
- Login uses scrypt password hashes, an **HTTP-only, SameSite=Lax session cookie** and a rate limit on failed logins.
- **Customers only ever see their own data.** `/me/*` routes take the customer from the session, never from the URL, and another customer's item returns 404 (no IDOR). Advisor routes need the advisor role (403 otherwise).
- Secrets live only in `.env` and `secrets/`, both git-ignored. The backend refuses to start without a strong `SESSION_SECRET`.
- All data is synthetic.

## Run it

Requirements: Docker, Node 20+ and **pnpm** (never npm).

```bash
cp .env.example .env
# Fill in: POSTGRES_PASSWORD, SESSION_SECRET (≥32 chars), DEMO_PASSWORD, GOOGLE_CLOUD_PROJECT
# Generate values with: python3 -c "import secrets; print(secrets.token_hex(24))"

# Gemini runs through Vertex AI with a service-account key (no API keys):
mkdir -p secrets && cp ~/Downloads/<your-key>.json secrets/gcp-sa-<name>.json
./scripts/use-gcp.sh <name>       # activates the key, sets the project, tests one Gemini call

docker compose up -d --build      # Postgres + FastAPI on :8000; migrates and seeds on start
cd frontend && pnpm install
printf 'NEXT_PUBLIC_API_URL=http://localhost:8000\nNEXT_PUBLIC_USE_MOCKS=false\n' > .env.local
pnpm dev                          # http://localhost:3000
```

Without Gemini credentials everything still works on the rule-based fallback. `NEXT_PUBLIC_USE_MOCKS=true` runs the frontend on its own, with mock data.

**Demo logins** (the password is `DEMO_PASSWORD` from your `.env`):

| User | Story |
|---|---|
| `sara` | Moving home: a €15,000 notary deposit and Immoweb searches. The twin shows a November pinch from notary fees. |
| `lien` | Growing family |
| `ahmed` | First job, no marketing consent, so offers are held |
| `marc` | Approaching retirement |
| `julie` | Financial stress: support only, never sales |
| `pieter` | Buying a car |
| `jan` | Routine. In the console, inject "Notary deposit" and watch him change live. |
| `advisor` | Console: 207 customers, review queue, customer detail with the twin chart and probability bars, scale view |

**Tests and evals:**
```bash
docker compose exec backend pytest -q                                   # 93 tests, including the API contract
docker compose exec -e OPENROUTER_API_KEY backend python -m evals.run   # full A/B, ~15 min
cd frontend && pnpm lint && pnpm build
```

## Project layout

```
backend/            FastAPI + SQLAlchemy + Alembic (Postgres)
  app/detection/    rules.py, gemini.py (Vertex, structured output), jev.py (eval variant)
  app/twin.py       12-month forecast and pinch points
  app/interventions.py  catalog + guardrail policy
  app/routers/      /auth, /me (customer), advisor routes
  evals/            A/B runner, labelled dataset, hard cases, REPORT.md
  tests/            93 tests
frontend/           Next.js (App Router, Tailwind): /login, /app, /advisor, /advisor/customers/[id], /advisor/scale
openspec/           the spec: proposal, capability specs, design (API contract), tasks
scripts/use-gcp.sh  switch the Gemini service account
```

## What's unfinished

- **Gemini on the organizers' project.** The hackathon project (`qwiklabs-gcp-02-…`) has an org policy (`vertexai.allowedModels`) that currently denies every model. Until it's lifted, detection there uses the rule-based fallback; our own project runs Gemini (`./scripts/use-gcp.sh <name>`).
- **The Jev-first cascade** is simulated in the evals but not wired into the app. It would make live analysis about 10× faster at the median (0.3 s against 3.1 s) and 5× cheaper, at the same accuracy.
- **Price assumptions:** the Gemini cost projection uses placeholder token prices.
- **Proof-of-concept shortcuts:**
  - The rate limiters are in memory (one process).
  - Analysis runs inside the request; production would use an event-driven queue.
  - The email and advisor channels are labels only.
  - The data is synthetic.
- **Stretch goals not built:** Gemini-written card messages, and ElevenLabs voice notes.

## How we built it

We planned with **OpenSpec** (`openspec/changes/kbc-foresight/`) and split into two parallel streams around a frozen API contract with mock fixtures: backend (data, detection, twin, guardrails, auth, evals) and frontend (customer app, advisor console, scale view). A contract test keeps the mocks and the real API in sync.
