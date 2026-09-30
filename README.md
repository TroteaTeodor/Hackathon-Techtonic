# KBC Foresight

**Tectonic Hackathon: KBC track.** A proof of concept for how a bank can understand what each customer needs and help at exactly the right moment, for 2.3 million customers at once.

> A life moment isn't just a sales trigger: it rewrites a customer's financial future.
> Foresight spots the moment, projects what it will do to the next 12 months, and helps **before** the pinch.

## The idea

| Step | What happens | How |
|---|---|---|
| **1. Signals** | Transactions, app events, searches and contacts with the bank | Synthetic data: 7 scripted story customers and 200 generated ones |
| **2. Understand** | Which life moment is this customer in? Moving home, a baby, a new job, retirement, buying a car, travelling abroad, financial stress, or nothing special | A **Jev-first cascade**. **Jev** (OpenRouter's Decisions API) answers typed questions with calibrated probabilities: the moment, stress and receptiveness. When Jev is under 75% sure, **Gemini 3.8 Flash** (Vertex AI) decides. Keyword rules are the safety net, so detection never fails. |
| **3. Foresee** | A **financial twin**: a 12-month cash-flow forecast | Deterministic arithmetic (no AI, so every number is explainable): recurring and yearly payments, plus what the detected moment adds (notary fees, a mortgage, childcare…), with **pinch points** where the balance drops below €250 |
| **4. Act** | The right help across banking, insurance and investing | An intervention catalog and an ordered **guardrail policy** (below). Pinch-point warnings go out 21 days before the month. |
| **5. Explain** | Every card carries a "Why am I seeing this?" | The reasons name the signals, the probability and the rule that applied |
| **6. Understand spending** | Every transaction is categorised (17 categories), recurring payments are flagged, subscriptions are detected with price-rise alerts, and spend is broken down by category | Deterministic merchant rules. Large one-offs, like a notary deposit, aren't counted as monthly spend |
| **7. Personalise** | Cards say what we noticed and ask: *"We noticed a €15,000 payment to Notaris Peeters. Are you moving?"*, with one direct action (**Get home insurance**). Up to 2 spending-based suggestions are added | **Gemini Flash** rewrites the wording and picks the suggestions in the background. The output is validated: only known offers, no invented numbers, and the "We noticed" sentence is kept word for word. It's never used for customers in financial difficulty. The guardrails still decide what may be shown |

**Guardrails**, applied in order:
1. A customer in financial difficulty gets **support, never sales**, routed to an advisor.
2. No marketing without consent.
3. "Not the right time" holds offers.
4. The customer's proactivity setting (minimal, balanced or proactive) sets the confidence needed.
5. Uncertain cases (50–75% confidence) go to an advisor.
6. Everything else is sent automatically.

When a customer says "Not right", that moment is never assigned to them again.

**Scale:** only customers with new signals are re-analysed, and the twin is cheap arithmetic. The advisor console's scale view shows the share handled automatically and projects the cost to 2.3M customers.

## Design decisions, and the numbers behind them

Every choice below was measured, not assumed. We A/B-tested on **340 labelled cases**:
- the 7 story customers
- the 200 generated customers
- **133 hard cases**. 86 are *paraphrases*: moments described without any obvious keyword, such as adoption fees, movers plus a rental guarantee, or an eSIM for Norway. 34 are *traps*: a keyword that points the wrong way, such as a notary for an inheritance or a gift for someone else's baby. The other 13 are hand-written.

Metrics:
- **Accuracy** and **macro-F1**
- **Calibration error (ECE)**: how far the stated confidence is from the real hit rate
- **Latency** (p50 / p95)
- **Cost**
- **Guardrail outcomes**, computed on the interventions each variant actually produces
- Significance from an **exact McNemar test** on the paired predictions

Raw results: [`backend/evals/REPORT.md`](backend/evals/REPORT.md). Run it yourself with `python -m evals.run`.

### 1. Detection: Jev first, Gemini only when Jev is unsure

| Design | Accuracy | Macro-F1 | Hard cases | Stress recall | Calibration error | p50 / p95 | Calls > 10 s | Cost / 1k* | Per day at 2.3M × 5% |
|---|---|---|---|---|---|---|---|---|---|
| Keyword rules | 61.8% | 0.645 | 2.3% | 39.4% | 0.172 | — | — | €0 | €0 |
| Jev only | 94.1% | 0.953 | 96.2% | 100% | 0.023 | 0.3 / 0.5 s | 0 | €0.10 | €11 |
| Gemini 3.8 Flash only | 96.5% | 0.971 | 98.5% | 97.0% | 0.060 | 3.1 / 9.9 s | 16 | €1.14 | €131 |
| **Jev → Gemini cascade (shipped, measured live)** | **96.2%** | **0.969** | **97.7%** | **100%** | **0.021** | **0.3 / 3.8 s** | **6** | **€0.25** | **€28** |

**How it works:**
1. Jev (OpenRouter's Decisions API) answers typed questions: a `choice` for the moment, a `noul` for stress, and a `score` for receptiveness.
2. When its confidence is below 75%, the customer is escalated to Gemini 3.8 Flash.
3. If both fail, the keyword rules answer.

**Why:**
- **Detection is classification, not text generation.** The guardrail policy asks typed questions about a fixed list of moments, which is exactly what a decision model is built for.
- **Calibration matters more than raw accuracy**, because the policy acts on the numbers: it holds offers below 75%, sends 50–75% to an advisor, and switches to support-only at a stress score of 0.6. The cascade has the lowest calibration error of any variant (**0.021**). When Jev is at least 75% confident, it's right **99.3%** of the time (300 cases).
- **No accuracy is lost.** The cascade and Gemini-alone disagree on only 7 of 340 cases, split 3 to 4 (**p = 1.0**, no difference).
  - Jev answers **87%** of customers, and is right **99.0%** of the time on those.
  - The hardest **12.6%** go to Gemini, which recovers Jev's misses: the cascade beats Jev alone 10 cases to 3.
- **About 10× faster at the median** (0.3 s against 3.1 s): the live "inject a signal" demo updates in 0.4 s instead of 5–8 s.
- **5× cheaper:** about **€28 a day** for 2.3M customers against €131 for Gemini alone.
- **It never fails:**
  - If OpenRouter is down, Gemini answers.
  - If Vertex is down, Jev's answer is kept, not the keyword rules.
  - If both are down, the rules answer.
  - The console shows which model decided.
- **The rules are only a safety net.** They score 100% on the generated customers, because those are built from the same keywords, but **0%** on paraphrases and **5.9%** on traps. That's why the hard-case set exists: without it, the rules would look perfect.

\* Jev's cost is what OpenRouter bills, in USD, treated as EUR. Gemini's cost uses the placeholder token prices in `.env` (`PRICE_PER_MILLION_*`).

### 2. Which Gemini, for the escalations

| Variant | Accuracy | Hard cases | p50 / p95 | Calls > 10 s | Fallbacks | Cost / 1k |
|---|---|---|---|---|---|---|
| **Gemini 3.8 Flash, low thinking (used)** | **96.5%** | **98.5%** | **3.1 / 9.9 s** | **16** | **1.2%** | **€1.14** |
| Gemini 3.8 Flash, default thinking | 95.9% | 96.2% | 5.8 / 16.5 s | 58 | 2.4% | €1.99 |
| Gemini 3.5 Flash, low thinking | 95.6% | 94.0% | 2.4 / 27.5 s | 40 | 6.2% | €1.30 |

- **Low thinking over default:** the accuracy is the same (p = 0.69), but low is 2× faster and 43% cheaper, with 3.6× fewer slow calls.
- **3.8 Flash over 3.5 Flash:** the accuracy is again the same (p = 0.63), but 3.8 has a far better worst case (9.9 s against 27.5 s at p95), 5× fewer fallbacks, and is stronger on the hard cases.

### 3. Guardrails before personalisation

These are measured on the interventions each variant actually produced:

| | Stressed customer got a sales offer | No consent, got a sales offer | Harmful sales rate (true stress cases sold to) | Right moment reached | Wrong moment delivered |
|---|---|---|---|---|---|
| Keyword rules | 0 | 0 | 3.0% | 23.5% | 1.8% |
| **Cascade (shipped)** | **0** | **0** | **0%** | **73.2%** | **0.6%** |

- The policy is an **ordered list of rules** in one module (see [the idea](#the-idea)). Every card carries the reasons that produced it, so each decision can be explained and audited.
- The **rules on their own are unsafe.** They miss 61% of financially stressed customers (39.4% stress recall), so 3% of true stress cases would be sold to. Every AI variant got that to **0%**.
- The cascade reaches the right customer with a relevant offer **3× as often** as the rules (73.2% against 23.5%), and sends a wrong-moment offer to only 0.6% of customers.
- A customer who says "Not right" never gets that moment again, even after new signals.

### 4. The financial twin is arithmetic, not AI

The 12-month forecast is deterministic:
- recurring payments (seen in at least 3 of 12 months)
- yearly payments (only when they look periodic, such as insurance or taxes, so a notary deposit doesn't come back next year)
- a small table of what each moment adds

The reasons:
- **Every euro can be checked**, which a bank needs.
- It **costs nothing** at 2.3M customers.
- It **recomputes instantly** when a signal arrives.

An LLM forecast would be slow, costly and impossible to audit. The AI is used only where judgement is needed: reading the signals.

### 5. Built to scale

- **Incremental:** a customer is re-analysed only when a new signal arrives or a preference changes. Listing customers never re-runs detection; a test checks this.
- **Cost projection:** at a 5% daily re-analysis rate, the cascade costs about **€28 a day** for 2.3M customers. The console's scale view shows the live figure, with its assumptions.
- **Automation:** the policy sends high-confidence cases automatically and puts only the uncertain or sensitive ones in front of an advisor.
- **Production path:** an event queue instead of analysing inside the request, and batch re-scoring. See [what's unfinished](#whats-unfinished).

### 6. Contract-first, two parallel streams

- We wrote the API contract and mock data first, then built the backend and frontend in parallel without blocking each other.
- A **contract test** checks every mock file against the real Pydantic schemas, so the two sides can't drift apart.
- The work was planned with **OpenSpec** ([`openspec/changes/kbc-foresight/`](openspec/changes/kbc-foresight/)): the proposal, 7 capability specs, the design (with the full reasoning behind decision 1) and the task list.

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

# Jev: set OPENROUTER_API_KEY. Gemini (for cases where Jev is unsure) runs through Vertex AI with a service-account key:
mkdir -p secrets && cp ~/Downloads/<your-key>.json secrets/gcp-sa-<name>.json
./scripts/use-gcp.sh <name>       # activates the key, sets the project, tests one Gemini call

./scripts/dev.sh                  # everything: Postgres + API on :8000 and the frontend on :3000
./scripts/dev.sh --reset          # same, but wipe the database first so it's re-seeded from scratch
```

The database **seeds itself**. On every start, the backend runs the migrations, then fills an empty database with the 7 story customers, 200 generated customers and the demo logins. If the data is already there, it's left alone. By hand, the steps are `docker compose up -d --build`, then `cd frontend && pnpm install && pnpm dev`.

Without AI credentials everything still works on the rule-based fallback. `NEXT_PUBLIC_USE_MOCKS=true` runs the frontend on its own, with mock data.

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
docker compose exec backend pytest -q                                   # 101 tests, including the API contract
docker compose exec -e OPENROUTER_API_KEY backend python -m evals.run   # full A/B, ~15 min
cd frontend && pnpm lint && pnpm build
```

## Project layout

```
backend/            FastAPI + SQLAlchemy + Alembic (Postgres)
  app/detection/    __init__.py (the cascade), jev.py (first step), gemini.py (escalation), rules.py (safety net)
  app/twin.py       12-month forecast and pinch points
  app/interventions.py  catalog + guardrail policy
  app/routers/      /auth, /me (customer), advisor routes
  evals/            A/B runner, labelled dataset, hard cases, REPORT.md
  tests/            101 tests
frontend/           Next.js (App Router, Tailwind): /login, /app, /advisor, /advisor/customers/[id], /advisor/scale
openspec/           the spec: proposal, capability specs, design (API contract), tasks
scripts/use-gcp.sh  switch the Gemini service account
```

## What's unfinished

- **Gemini on the organizers' project.** The hackathon project (`qwiklabs-gcp-02-…`) has an org policy (`vertexai.allowedModels`) that denies every model. With that account, Jev still answers every customer, but the ~13% escalations can't reach Gemini and keep Jev's answer instead. We run Gemini on our own Google Cloud project (`./scripts/use-gcp.sh <name>`).
- **Price assumptions:** the Gemini cost projection uses placeholder token prices.
- **Eval numbers** were measured before the subscription and everyday-spending data was added to the synthetic customers. Re-run with `python -m evals.run` to refresh them.
- **Proof-of-concept shortcuts:**
  - The rate limiters are in memory (one process).
  - Analysis runs inside the request; production would use an event-driven queue.
  - The email and advisor channels are labels only.
  - The data is synthetic.
- **Stretch goals not built:** Gemini-written card messages, and ElevenLabs voice notes.

## How we built it

See [design decision 6](#6-contract-first-two-parallel-streams).
- **Backend:** data, detection, twin, guardrails, auth and evals.
- **Frontend:** customer app, advisor console and scale view.
- **Security:** audited with Aikido from the first commit.
