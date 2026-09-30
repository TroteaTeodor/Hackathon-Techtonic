# Tasks

Owners:
- **[Both]**: the shared foundation, done together on one branch.
- **[A]**: workstream A (backend) on `feat/backend`.
- **[B]**: workstream B (frontend) on `feat/frontend`.

When the whole change is done and merged, archive it (`/opsx:archive`).

Groups 2–6 (A) and 7–10 (B) run in parallel and never touch each other's directories. Times are targets from the start of the 3 hours. Items marked *(cut line)* are the first to drop if a stream runs late.

## 1. Foundation [Both] (0:00–0:15)

- [x] 1.1 Land the `add-github-mcp` and `jev-categorization` work on `main` (done in the `initial commit`; jev brings Alembic, and its `items` code is removed in 2.1). Verify `git log origin/main` shows `initial commit`.
- [x] 1.2 On a `foundation` branch, write `frontend/src/lib/types.ts` exactly as in design.md "Types". Verify `pnpm exec tsc --noEmit` passes in `frontend/`.
- [x] 1.3 Write the fixtures in `frontend/src/mocks/` (`me-customer`, `me-advisor`, `overview-sara`, `customers`, `customer-detail-sara`, `customer-detail-jan`, `customer-detail-after-inject`, `scale`). Sara's moving-home story has a November pinch point. Jan (routine) has a before and after state for the notary-deposit injection. Together they cover the `delivered`, `review` and `dismissed` statuses; `held` appears in the scale counts. Verify every file parses with `node -e "JSON.parse(...)"`.
- [x] 1.4 Update `.env.example` with `GEMINI_API_KEY`, `GEMINI_MODEL`, `SESSION_SECRET`, `DEMO_PASSWORD` and `COOKIE_SECURE`, with placeholders only, and remove `OPENROUTER_API_KEY`. Verify `git diff` contains no real values.
- [x] 1.5 Merge the `foundation` PR into `main`, then create `feat/backend` (A) and `feat/frontend` (B) from it. Verify both branches exist on `origin`.
- [ ] 1.6 Connect the repo to Aikido and run the AI Code Audit baseline. Verify the "before" screenshot is saved for submission.

## 2. Data model and synthetic customers [A] (0:15–0:45)

- [ ] 2.1 Remove the `items` model, schemas, routes and Jev client, and add models for `users`, `customers`, `signals`, `moments` and `interventions` per design.md decision 8. Add an Alembic migration that drops `items` and creates them. Verify that `docker compose down -v && docker compose up -d --build` starts, and `alembic current` shows the new head.
- [ ] 2.2 Add Pydantic schemas mirroring every contract type, and a pytest contract test that validates each file in `/contract-fixtures` (mount `./frontend/src/mocks` read-only in compose). Verify `docker compose exec backend pytest -q tests/test_contract.py` passes.
- [ ] 2.3 Write the seed script: 7 story customers (Sara moving home, Lien growing family, Ahmed new job, Marc approaching retirement, Julie financial stress, Pieter buying a car, Jan routine), each with 12 months of transactions (salary, rent, utilities, groceries, one yearly insurance premium) and recent signals. Add demo users with `DEMO_PASSWORD`, run it idempotently on startup, and use only synthetic names, IBANs and contacts. Verify two restarts leave exactly 7 story customers, and that a pytest checks idempotency.
- [ ] 2.4 Generate 200+ population customers from templates with `random.Random(42)`. Verify that two fresh seeds give identical counts and names in a pytest. *(cut line: drop to 50)*

## 3. Life-moment detection [A] (0:45–1:10)

- [ ] 3.1 Write rule-based detection: keyword and amount rules over the latest 40 signals, producing a full `Moment` with probabilities normalized to 1, stress (missed payments, overdraft, collection agency), receptiveness and rationale. Tune the rules so all 7 story customers get their scripted moment, and Jan gets `no_clear_moment`. Verify with a pytest per story customer.
- [ ] 3.2 Write Gemini detection with `google-genai`: structured output schema, only the customer's own profile and signals in the prompt, a 10 s timeout, validation of keys and probability sum, and a fallback to rules on any failure. Record input and output tokens. Verify a pytest with a mocked client covers a valid response, a malformed one (falls back to `rules`) and a timeout; also do a manual run with a real key on Sara, which should return source `gemini` and `moving_home`.
- [ ] 3.3 Analyze story customers at seed time (with Gemini when a key is set) and the population with rules only. Verify that `select source, count(*) from moments group by source` shows the expected split.

## 4. Financial twin [A] (1:10–1:35)

- [ ] 4.1 Detect recurring items (at least 3 of the last 12 months with similar amounts) and yearly items (seen once, projected to the same calendar month). Build 12 months of income, expenses, balance and events. Verify pytests for a monthly salary and a yearly March premium.
- [ ] 4.2 Apply the moment adjustment table from design.md decision 2 only when confidence is at least 0.5, tagging events `moment`. Verify with a pytest that Sara's forecast has notary, moving and mortgage events, and that a 0.4-confidence moment adds none.
- [ ] 4.3 Detect pinch points (balance below €250), with the reason naming the largest expense that month. Verify with a pytest that Sara has a pinch point in her notary month, with a reason mentioning notary fees.

## 5. Interventions and guardrails [A] (1:35–1:55)

- [ ] 5.1 Build the intervention catalog covering every moment except `no_clear_moment`, plus pinch point and surplus. Each entry has a title, a message using `{first_name}`, a line and a channel. Verify a pytest asserts coverage.
- [ ] 5.2 Implement the policy as an ordered rule list per the `proactive-interventions` spec, returning status plus reasons. Set `deliver_at` 21 days before the pinch month. Keep feedback and advisor decisions across re-analysis. Verify pytests for Julie (support in review, no sales delivered), Sara (moving home delivered), no-consent customers (sales held), `minimal` proactivity, and the 2027-03 pinch dated 2027-02-08.
- [ ] 5.3 Write `analyze(customer)` as detection, then twin, then policy, persisting the moment and interventions. It runs only on a new signal, a preference change or a moment rejection. Verify with a pytest that listing customers twice triggers no detection call.

## 6. Access control and API routes [A] (1:55–2:15)

- [ ] 6.1 Add sessions: scrypt password hashes, a PyJWT HS256 cookie (`HttpOnly`, `SameSite=Lax`, 8 h, `Secure` via `COOKIE_SECURE`), and a startup failure when `SESSION_SECRET` is missing or under 32 characters. Add a login rate limit of 5 failures per 5 minutes per username and IP, returning 429. Verify pytests for a good login, a bad login with a generic 401, the 6th attempt returning 429, and the missing secret failing startup.
- [ ] 6.2 Add `/auth/*` and `/me/*` routes with `require_customer` (no customer ID parameters; interventions filtered by `id` and `customer_id`). Verify pytests: no cookie gives 401, and Sara giving feedback on Julie's intervention gives 404 with Julie's intervention unchanged.
- [ ] 6.3 Add advisor routes (`/customers`, `/customers/{id}`, `/customers/{id}/signals`, `/interventions/{id}/decision`, `/scale`) with `require_advisor`, and restrict CORS to the configured origins with credentials. Verify pytests: a customer calling `/customers` gets 403; injecting the notary preset for Jan changes his moment to `moving_home`; a `/scale` response validates against `ScaleStats`.
- [ ] 6.4 Document backend run, env vars and demo users in `CLAUDE.md` under "Running locally", and open the `feat/backend` → `main` PR. Verify the full `pytest -q` is green and the PR is open.

## 7. Frontend foundation and login [B] (0:15–0:40)

- [ ] 7.1 Write `src/lib/api.ts`: one typed function per contract endpoint, `credentials: "include"`, and a mock mode (`NEXT_PUBLIC_USE_MOCKS=true`) that returns fixtures after 300 ms. Mock inject returns `customer-detail-after-inject`. Verify with `pnpm lint` and `pnpm build`.
- [ ] 7.2 Replace the starter page. `/` routes by `GET /auth/me` role (to `/app`, `/advisor` or `/login`). Add the `/login` form with a generic error message, a logout control in the layout, and the navy and cyan theme tokens. Verify in mock mode that logging in as a customer lands on `/app` and as an advisor lands on `/advisor`, with a screenshot via Playwright MCP.
- [ ] 7.3 Add a reusable `TwinChart` component: balance line for 12 months, a €250 buffer line, pinch points marked, and `moment` events visually distinct. Verify it renders the `overview-sara` fixture with the March pinch point visible.

## 8. Customer app [B] (0:40–1:20)

- [ ] 8.1 Build `/app` in a phone frame (max-width about 420px): name, balance, `TwinChart`, and upcoming events for the next 3 months. Verify with a Playwright screenshot at 375×812 with no horizontal scroll.
- [ ] 8.2 Add the moment banner, shown only when confidence is at least 0.5, with friendly wording per moment key and a "Not right" button calling `POST /me/moment/reject`. Verify in mock mode that Sara sees "Looks like you're moving home".
- [ ] 8.3 Add intervention cards (delivered only): title, message, line badge, date, a "Why am I seeing this?" toggle showing the reasons, and Helpful / Not relevant buttons (not relevant hides the card). Verify in mock mode that the reasons toggle works and dismiss hides the card.
- [ ] 8.4 Add the proactivity selector (minimal, balanced, proactive) calling `PUT /me/preferences` and re-rendering. Verify in mock mode that the selector updates without a reload.

## 9. Advisor console [B] (1:20–2:00)

- [ ] 9.1 Build `/advisor`: a customer table (name, age, city, moment chip with confidence, stress indicator, next pinch month, review count), with a moment filter and a "needs review" toggle. Verify in mock mode that the filters narrow the fixture list correctly.
- [ ] 9.2 Build `/advisor/customers/[id]` (via `useParams`):
  - profile, consent and proactivity
  - signal timeline
  - moment probability bars, with stress, receptiveness, rationale and a source badge
  - `TwinChart`
  - interventions with status, channel, date, reasons and feedback
  - Approve / Dismiss buttons on `review` items

  Verify in mock mode with a screenshot of Sara's detail.
- [ ] 9.3 Add the inject-signal panel: presets (notary deposit -€15,000, baby-store purchase, missed loan payment, car dealer quote) and a free-form form (kind, description of at most 200 characters, amount). It updates the page in place from the response and highlights what changed. Verify in mock mode that the notary preset swaps in the after-inject fixture without a reload.

## 10. Scale view [B] (2:00–2:15) *(cut line: fold into the /advisor header)*

- [ ] 10.1 Build `/advisor/scale`: population, moment distribution bars, interventions by status with the automation rate, average tokens and cost per analysis, and the projected daily and monthly cost for 2.3M customers, with every assumption printed. Verify in mock mode with a screenshot showing the projection and its assumptions.
- [ ] 10.2 Write the README pitch section: the problem, the idea (moments + twin), the guardrails, scale, how to run, and what's unfinished. Open the `feat/frontend` → `main` PR. Verify `pnpm lint` and `pnpm build` pass and the PR is open.

## 11. Integration and security [Both] (2:15–2:40)

- [ ] 11.1 Merge both PRs into `main`. Run `docker compose up -d --build` and `pnpm dev` with `NEXT_PUBLIC_USE_MOCKS=false`. Walk the demo path end to end: Sara's app, Jan's inject and adaptation, Julie's guardrail, approving a review item, and the scale view. Verify that every step works against the real API (Playwright screenshots).
- [ ] 11.2 Run a manual security check: a customer session calling `/customers` gets 403, Sara's feedback on another customer's intervention ID gets 404, no cookie gets 401, and `git grep -iE "key|secret|password"` shows no real values. Verify each result is recorded in the PR description.
- [ ] 11.3 Re-run the Aikido AI Code Audit, fix the findings on a `fix/aikido` branch, merge via a PR, and mark them resolved. Verify the "after" screenshot is saved.

## 12. Submission [Both] (2:40–3:00)

- [ ] 12.1 Record the demo video (under 3 minutes) following the script in the plan. Verify the length and that the upload link opens logged out.
- [ ] 12.2 Fill in Builderbase: description, video link, public repo link, Aikido before and after screenshots. Verify the repo is public and every link opens in a private window.

## 13. Optional stretch [A or B, only if 11 is green]

- [ ] 13.1 Gemini writes each card's message in the customer's tone (it replaces the catalog text; falls back to the catalog). Verify Sara's card text differs from the catalog template and still states the amount and date.
- [ ] 13.2 ElevenLabs voice note on the top card in Dutch, with a play button in `/app`. Verify it plays in the demo, with the key only in `.env`.
