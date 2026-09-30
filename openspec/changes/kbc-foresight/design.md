# Design

## Context

- **Repo today:** `main` has the starter: Next.js 16 in `frontend/`, FastAPI with SQLAlchemy 2 in `backend/`, and Postgres via `docker compose`. It also has Alembic migrations, a demo `items` table with Jev categorization (to be removed), and the Playwright and GitHub MCP configs.
- **Constraints:**
  - 2 builders, 3 hours, one demo video under 3 minutes.
  - Security audit by Aikido (10% of the score).
  - pnpm only.
  - Feature branches merge into `main` via PRs.
  - No AI attribution in commits.
- For motivation and scope, see `proposal.md`. For behavior, see `specs/`.

## Goals / Non-Goals

**Goals:**
- Two workstreams that never wait on each other after a 15-minute shared foundation.
- A demo that works with or without working Gemini credentials (rule-based fallback), and with or without the backend (frontend mock mode).
- Security that holds up in an audit: sessions, roles, per-customer scoping.

**Non-Goals:**
- Real KBC data, real banking integrations, or production deployment.
- Real model calibration or accuracy evaluation.
- Internationalization. The UI is in English, and names and merchants are Belgian.
- Rendering channels other than the app. Email and advisor channels are labels only.

## Workstreams, ownership and branches

| | Workstream A: backend | Workstream B: frontend |
|---|---|---|
| Branch | `feat/backend` | `feat/frontend` |
| Owns | `backend/`, `docker-compose.yml`, `.env.example` | `frontend/`, `README.md` (pitch section) |
| Capabilities | synthetic-customers, life-moment-detection, financial-twin, proactive-interventions, access-control | customer-app, advisor-console |
| Builds against | Postgres, Gemini | Mock fixtures in `frontend/src/mocks/`, then the real API |

**Shared, frozen after the foundation:** the API contract below, `frontend/src/lib/types.ts`, and `frontend/src/mocks/*.json`. A change to them is a tiny PR that both people agree on. Nobody edits the other's directories. The only files both may touch are `CLAUDE.md` and the README, and only in the final 15 minutes.

**Timeline:**

| Time | Who | What |
|---|---|---|
| 0:00–0:15 | Together | Foundation (tasks group 1) lands on `main`; Aikido baseline scan |
| 0:15–2:15 | Parallel | A and B build their groups; each merges small PRs to `main` whenever green |
| 2:15–2:40 | Both | Integration: B switches mocks off; Aikido re-scan and fixes |
| 2:40–3:00 | Both | Demo video, README, submission |

## API contract (frozen)

- **Base URL:** `NEXT_PUBLIC_API_URL`, default `http://localhost:8000`.
- **Requests:** the frontend always sends `credentials: "include"`, with JSON bodies.
- **Errors:** `{"detail": "..."}` (always a string) with status 401, 403, 404, 409 (a decision on an intervention that isn't in review), 422 or 429.

### Auth
| Method & path | Role | Body | Response |
|---|---|---|---|
| `POST /auth/login` | none | `{username, password}` | `Me`, plus sets the `session` cookie |
| `POST /auth/logout` | none | none | `204`, clears the cookie |
| `GET /auth/me` | any | none | `Me` |

### Customer (identity comes from the session, never from the URL)
| Method & path | Body | Response |
|---|---|---|
| `GET /me/overview` | none | `CustomerOverview` |
| `PUT /me/preferences` | `{proactivity}` | `CustomerOverview` (re-analyzed) |
| `POST /me/moment/reject` | none | `CustomerOverview` (the moment is set to `no_clear_moment`, source `customer`) |
| `POST /me/interventions/{id}/feedback` | `{feedback: "helpful"\|"not_relevant"}` | `CustomerOverview`; 404 if the intervention isn't theirs |

### Advisor
| Method & path | Body | Response |
|---|---|---|
| `GET /customers?moment=&needs_review=&limit=&offset=` | none | `CustomerSummary[]` (`limit` 1–1000, default 500) |
| `GET /customers/{id}` | none | `CustomerDetail` |
| `POST /customers/{id}/signals` | `SignalCreate` | `CustomerDetail` (re-analyzed) |
| `POST /interventions/{id}/decision` | `{decision: "approve"\|"dismiss"}` | `Intervention` |
| `GET /scale` | none | `ScaleStats` |

### Types (mirrored as Pydantic in `backend/app/schemas.py` and TypeScript in `frontend/src/lib/types.ts`)

```ts
type Role = "customer" | "advisor";
type MomentKey = "moving_home" | "growing_family" | "new_job" | "approaching_retirement"
  | "buying_car" | "travel_abroad" | "financial_stress" | "no_clear_moment";
type Proactivity = "minimal" | "balanced" | "proactive";

interface Me { role: Role; display_name: string }

interface CustomerProfile {
  id: number; first_name: string; last_name: string; age: number; city: string;
  marketing_consent: boolean; proactivity: Proactivity; balance: number;
}
interface Signal {
  id: number; date: string /* YYYY-MM-DD */; description: string; amount: number | null;
  kind: "transaction" | "app_event" | "search" | "contact";
}
interface SignalCreate {
  kind: Signal["kind"]; description: string /* 1..200 */; amount?: number | null; date?: string;
}
interface Moment {
  key: MomentKey; label: string; confidence: number;
  probabilities: Record<MomentKey, number>;
  stress: number; receptiveness: 0 | 1 | 2; rationale: string;
  source: "gemini" | "rules" | "customer"; analyzed_at: string /* ISO */;
}
interface TwinEvent {
  label: string; amount: number; kind: "income" | "expense";
  source: "recurring" | "scheduled" | "moment";
}
interface TwinMonth {
  month: string /* YYYY-MM */; income: number; expenses: number; balance: number;
  events: TwinEvent[];
}
interface PinchPoint { month: string; balance: number; reason: string }
interface Twin { start_balance: number; months: TwinMonth[]; pinch_points: PinchPoint[] }
interface Intervention {
  id: number; key: string; title: string; message: string;
  line: "banking" | "insurance" | "investing" | "support";
  channel: "app" | "email" | "advisor";
  status: "delivered" | "review" | "held" | "dismissed";
  deliver_at: string /* YYYY-MM-DD */; reasons: string[];
  feedback: "helpful" | "not_relevant" | null;
}
interface CustomerOverview {
  customer: CustomerProfile;
  moment: Moment | null;
  twin: Twin;
  interventions: Intervention[]; // delivered only, not_relevant excluded
}
interface CustomerSummary {
  id: number; name: string; age: number; city: string;
  moment_key: MomentKey | null; moment_confidence: number | null; stress: number | null;
  next_pinch_month: string | null; review_count: number;
}
interface CustomerDetail {
  customer: CustomerProfile; signals: Signal[] /* newest first */;
  moment: Moment | null; twin: Twin;
  interventions: Intervention[]; // all statuses
}
interface ScaleStats {
  population: number;
  moments: Record<MomentKey, number>;
  interventions: Record<Intervention["status"], number>;
  automation_rate: number;        // delivered / (delivered + review)
  avg_tokens_per_analysis: number;
  avg_cost_per_analysis_eur: number;
  assumptions: {
    customers: number /* 2300000 */; daily_reevaluation_rate: number /* 0.05 */;
    price_per_million_input_tokens_eur: number; price_per_million_output_tokens_eur: number;
  };
  projected_daily_cost_eur: number; projected_monthly_cost_eur: number;
}
```

Fixtures (`frontend/src/mocks/`): `me-customer.json`, `me-advisor.json`, `overview-sara.json`, `customers.json`, `customer-detail-sara.json`, `customer-detail-jan.json` (routine, before injection), `customer-detail-after-inject.json` (Jan after the notary deposit) and `scale.json`. They are the canonical examples of the types above. A contract test in A validates them against the Pydantic schemas, and the compose file mounts them read-only into the backend container at `/contract-fixtures`.

## Decisions

**1. Moment detection is a Jev-first cascade: Gemini decides when Jev is unsure, and rules are the safety net.**

```
signals ──► Jev (OpenRouter Decisions API: choice, noul and score questions)
              │ confidence ≥ 75% ──► answer            (87% of customers, p50 0.3 s)
              │ below 75% or error
              ▼
            Gemini 3.8 Flash, low thinking (Vertex AI, structured output)
              │ ok ──► answer, "Escalated from Jev (x%)"  (the hardest ~13%)
              │ error
              ▼
            Jev's own answer if it had one, else the keyword rules  (never fails)
```

Why this design, from the A/B evals in `backend/evals/REPORT.md`. There were 340 labelled cases, including 133 hard traps and paraphrases; the `app` row is this pipeline running live:

| Design | Accuracy | Hard cases | Calibration error | p50 / p95 latency | Cost / 1k | Daily @ 2.3M × 5% |
|---|---|---|---|---|---|---|
| Keyword rules | 61.8% | 2.3% | 0.172 | — | €0 | €0 |
| Jev only | 94.1% | 96.2% | 0.023 | 0.3 s / 0.5 s | €0.10 | €11 |
| Gemini 3.8 Flash, low thinking only | 96.5% | 98.5% | 0.060 | 3.1 s / 9.9 s | €1.14 | €131 |
| **Jev → Gemini cascade (chosen)** | **96.2%** | **97.7%** | **0.021** | **0.3 s / 3.8 s** | **€0.25** | **€28** |

- **Detection is classification, not generation.** The policy asks typed questions about a fixed set of moments. Jev's Decisions API answers exactly that: a `choice` for the moment, a `noul` for stress, and a `score` for receptiveness.
- **Calibration matters more than raw accuracy**, because the guardrail policy acts on the numbers (thresholds of 0.5 and 0.75, stress at 0.6 or above). The cascade has the lowest calibration error of any variant. When Jev is 75% or more confident, it is right 99.0% of the time.
- **As accurate as Gemini alone.** The cascade and Gemini-low differ on only 7 cases, split 3 to 4 (exact McNemar p = 1). Against Jev alone, the cascade wins 10 cases to 3 (p = 0.092): the escalation is what recovers Gemini's edge on the ambiguous cases.
- **About 10× faster at the median, and 5× cheaper.** The live inject in the demo feels instant, the projection for 2.3M customers drops from about €131 to about €28 a day, and far fewer calls come near the 10 s request limit.
- **Resilient.** If OpenRouter is down, Gemini answers. If Vertex is down, Jev's calibrated answer is kept instead of falling to keyword rules. If both are down, the rules answer. Detection never fails, and the source is recorded (`jev`, `gemini`, `rules` or `customer`) and shown in the console.
- **Explainable.** Jev returns probabilities, not prose, so its rationale lists the customer's distinctive recent signals. Escalated cases carry Gemini's one-sentence rationale, prefixed with "Escalated from Jev (x%)".

Alternatives considered:
- **Gemini only** (the previous default): as accurate, but about 5× the cost, 10× slower at the median, and worse calibrated.
- **Jev only:** the cheapest and fastest, but 2 points less accurate, losing on the ambiguous cases.
- **Gemini with default thinking:** slower and costlier than low thinking, with no accuracy gain.
- **Keyword rules:** only a safety net (2.3% on hard cases).

Trade-offs:
- Two providers means two credentials: `OPENROUTER_API_KEY`, and the Vertex service account in `secrets/`.
- The Decisions API is an alpha.
- Jev's cost is what OpenRouter reports (USD, treated as EUR). Gemini's cost uses the configured `PRICE_PER_MILLION_*` placeholders.

Settings:
- `DETECTOR`: `cascade` (default), `jev`, `gemini` or `rules`.
- `JEV_ESCALATION_THRESHOLD`: default `0.75`.
- `GEMINI_MODEL`: `gemini-3.8-flash`, on Vertex location `global`, with `GEMINI_THINKING_LEVEL=low`.
- Seeding gets a 30 s budget and 2 retries on transient 429/5xx errors. Live requests keep the 10 s limit.

**2. The twin is deterministic arithmetic, not AI.**
- *Why:* numbers a judge can check, instant recomputation, and zero cost at 2.3M customers.
- *Alternative:* LLM forecasting, rejected as slow, costly and unexplainable.
- *Moment adjustments:* a small table in code, with amounts per moment:

| Moment | Adjustment |
|---|---|
| `moving_home` | Notary €9,000 plus moving €2,500 at month +2; rent replaced by a mortgage of €1,150 from month +3 |
| `growing_family` | Childcare -€550/month and child benefit +€170/month from month +4; baby gear -€1,200 at month +1 |
| `new_job` | The recent first salary is projected monthly; if there's none, a salary uplift of +€350/month |
| `approaching_retirement` | Income ×0.65 from month +6 |
| `buying_car` | -€4,000 deposit at month +1; loan -€320/month from month +2 |
| `travel_abroad` | -€1,800 at month +1 |
| `financial_stress` | No adjustment (the history already shows it) |

**3. The policy is an ordered rule list in one module.** It returns a status plus reasons, following the spec order exactly. That makes guardrails easy to demo and to audit. Implementation choices within the spec:
- Pinch-point warnings count as a service message, not sales. They skip the consent and proactivity rules, so they stay under `minimal` (as the customer-app spec requires).
- Under stress, the pinch warning becomes an advisor-routed `support` version.
- A surplus nudge is sales. It's held without consent or under `minimal`.
- A decision on an intervention that isn't in `review` returns 409.
- "Not right" is remembered per customer (`customers.rejected_moment`): later detections never assign that moment again, even after new signals.

**4. Sessions use a signed JWT in an HTTP-only cookie.**
- *How:* PyJWT with HS256, the key from `SESSION_SECRET` (at least 32 characters), claims `sub` (user ID), `role` and `exp` (8 hours). Cookie flags: `HttpOnly` and `SameSite=Lax`, plus `Secure` when `COOKIE_SECURE=true`.
- *Why it's enough:* `localhost:3000` and `:8000` are same-site, so Lax cookies flow with `credentials: "include"`. SameSite=Lax also blocks cross-site form POSTs, which covers CSRF for this proof of concept.
- *Alternative:* tokens in localStorage, rejected because they're exposed to XSS.
- *Passwords:* `hashlib.scrypt` with a per-user salt, so no extra dependency. Demo users (`advisor`, `sara`, `lien`, `ahmed`, `marc`, `julie`, `pieter`, `jan`) all use `DEMO_PASSWORD` from the environment. No password is committed.

**5. Authorization is enforced by FastAPI dependencies.**
- `require_customer` returns the session's customer. Customer routes take no customer ID parameter at all.
- Intervention lookups filter by both `id` and `customer_id`.
- `require_advisor` guards every advisor route.

**6. Rate limiting is an in-memory sliding window** keyed by (username, client IP). It's enough for a single-process proof of concept, and documented as such.

**7. Analysis runs synchronously on write.**
- Injecting a signal, changing preferences and rejecting a moment each run detection, then the twin, then the policy for that one customer, inside the request (under 10 s with the AI timeout).
- Story customers are analyzed at seed time. That uses Gemini when a key is present, and the analysis is cached in the `moments` table.
- *Alternative:* a background worker, which isn't needed at this scale. The pitch describes it as the production path: an event-driven queue plus batch re-scoring.

**8. Data model (one new Alembic migration that also drops `items`):**
- `users(id, username, password_hash, role, customer_id?)`
- `customers(id, first_name, last_name, age, city, marketing_consent, proactivity, balance, is_story)`
- `signals(id, customer_id, date, kind, description, amount?)`
- `moments(id, customer_id, key, confidence, probabilities json, stress, receptiveness, rationale, source, input_tokens, output_tokens, analyzed_at)`, with the latest row per customer being the current one
- `interventions(id, customer_id, key, title, message, line, channel, status, deliver_at, reasons json, feedback?)`, replaced on each analysis while keeping `feedback` and advisor decisions for the same `key`

The twin is computed on read from signals plus the current moment, and is not stored.

**9. Migration base:** `main` already has Alembic (revision `0001` creates `items`). A adds revision `0002`, which drops `items` and creates the Foresight tables.

**10. Frontend:**
- The App Router with client components that fetch through `src/lib/api.ts`. When `NEXT_PUBLIC_USE_MOCKS=true`, `api.ts` returns fixtures instead of calling the backend (with a simulated 300 ms delay).
- The twin chart is inline SVG or Recharts, whichever is faster for B.
- Styling uses a KBC-like navy and cyan palette, without the KBC logo.
- Routes: `/login`, `/app`, `/advisor`, `/advisor/customers/[id]`, `/advisor/scale`.
- Role routing happens client-side from `GET /auth/me`. The backend enforces access either way.

## Risks / Trade-offs

- [LLM probabilities are not calibrated] → Jev answers first with calibrated probabilities (calibration error 0.021); Gemini only decides the ~13% of cases where Jev is unsure, and its confidence is shown as "confidence" with conservative thresholds.
- [No or failed Gemini credentials during the demo] → The rule-based fallback is scripted to recognize every story customer. The UI shows the source (`gemini`/`rules`).
- [Contract drift between A and B] → Types and fixtures are frozen at 0:15, and the contract test runs in A's CI step (`pytest`). Integration starts at 2:15 at the latest, not at 2:55.
- [Merge conflicts] → Directory ownership is strict. Only `README.md` and `CLAUDE.md` are shared, and only at the end.
- [3-hour overrun] → Each group lists its cut line. The optional group (ElevenLabs voice, Gemini-written messages) is only started if integration is green.
- [In-memory rate limiter resets on restart and doesn't span processes] → Acceptable for a single-container proof of concept; documented in the README under "unfinished".
- [Aikido flags the default dev settings] → No default secrets. The backend refuses to start without `SESSION_SECRET`, and `.env.example` holds only placeholders.

## Migration Plan

1. The foundation PR merges into `main`: the spec, the frozen types and fixtures, and the `.env.example` keys.
2. `feat/backend` migration: `alembic upgrade head` drops `items` and creates the new tables. For local dev, `docker compose down -v` resets the database.
3. Rollback isn't needed for a hackathon proof of concept. Reverting the merge commits restores the starter.

## Open Questions

- None blocking. Resolved: Vertex AI on project `billem-499113`, location `global` (Gemini 3.x isn't served from `europe-west1`), model `gemini-3.8-flash`, authenticated with the service-account key at `secrets/gcp-sa.json`. It was verified with a live call. There is no API-key path. The hackathon-provided project (`qwiklabs-gcp-02-7084aced4e5c`) currently denies every model through its `vertexai.allowedModels` org policy; its key is staged at `secrets/gcp-sa-hackathon.json` for when the organizers allow Gemini.
