# Proposal

## Why

The KBC challenge asks for a scalable way for KBC to understand what 2.3M customers need and to respond at exactly the right moment. Banks usually react after the fact. We want to show a proof of concept in which KBC spots a customer's life moment from their signals, projects what that moment will do to their finances over the next 12 months, and helps *before* the pinch arrives. We have 3 hours and two builders, so the work must split into two parallel streams that don't block each other.

## What Changes

- **Synthetic customer population**: story customers with scripted life events (moving home, new baby, first job, retirement, financial stress, buying a car), plus a larger generated population for the scale view. All data is fake; no real personal data.
- **Life-moment detection**: Gemini reads a customer's recent signals and returns a life moment with probabilities, a financial-stress score, and receptiveness. A rule-based fallback keeps the demo working without an API key.
- **Financial twin**: a month-by-month 12-month cash-flow forecast built from recurring payments, scheduled yearly events, and adjustments for the detected moment. It flags pinch points where the balance drops below a safety buffer.
- **Proactive interventions**: a catalog of banking, insurance, investing and support actions, chosen by an explainable policy with guardrails. Stressed customers get support, never sales. Marketing requires consent. Low confidence goes to an advisor. Every action says why it was shown.
- **Access control**: login with customer and advisor roles. Customers only ever see their own data. Advisors see the console. Built in from the start for the Aikido security audit.
- **Customer app view**: a phone-style "your next 12 months" screen with the forecast, the detected moment, proactive cards, a proactivity setting, and feedback on cards.
- **Advisor console**: a customer list with moments and risk flags; a detail view with signals, probabilities, the twin chart and interventions with reasons; an "inject signal" action for the live demo; and a scale view projecting cost to 2.3M customers.
- **BREAKING (internal)**: the starter `items` demo (table, endpoints, page, and the Jev categorization on the `jev-categorization` branch) is removed and replaced by the Foresight domain.
- **Two workstreams**:
  - **A (backend)** covers data, detection, twin, interventions and access control.
  - **B (frontend)** covers the customer app and the advisor console.
  - They share a frozen API contract and mock fixtures, so B builds against mocks while A builds the real API.

## Capabilities

### New Capabilities
- `synthetic-customers`: generating the fake customer population and their transaction and app signals, including scripted life stories and injected signals.
- `life-moment-detection`: turning a customer's signals into a life moment with probabilities, a stress score and receptiveness, with an AI path and a rule-based fallback.
- `financial-twin`: the 12-month cash-flow forecast, moment adjustments and pinch-point detection.
- `proactive-interventions`: the action catalog, the guardrail policy, delivery status, timing, channel, reasons and customer feedback.
- `access-control`: authentication, roles, session handling and per-customer data isolation.
- `customer-app`: the customer-facing view of their future, cards, proactivity setting and feedback.
- `advisor-console`: the advisor customer list, customer detail, signal injection, review decisions and the scale view.

### Modified Capabilities
<!-- None: openspec/specs/ is empty; the starter items demo was never specified. -->

## Impact

- **Backend** (`backend/`): new models and an Alembic migration (customers, signals, moments, interventions, users); new routers; a Gemini client (`google-genai`); a session library (`PyJWT`); the seed generator. The `items` code is removed.
- **Frontend** (`frontend/`): new routes (`/login`, `/app`, `/advisor`, `/advisor/customers/[id]`, `/advisor/scale`); a typed API client with a mock mode; a chart for the twin. The starter page is replaced.
- **Config**: `.env` gains the Vertex AI settings (`GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GEMINI_MODEL`, and a service-account key in `secrets/`), `SESSION_SECRET` and `DEMO_PASSWORD`. `OPENROUTER_API_KEY` is no longer used.
- **Repo process**: foundation lands on `main` first, then two branches (`feat/backend`, `feat/frontend`) merge into `main` via PRs. The Aikido baseline scan runs before feature work, and a re-scan runs after.
