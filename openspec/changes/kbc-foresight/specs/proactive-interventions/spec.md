# Spec Delta

## Purpose

Turns understanding (moment, stress, forecast) into the right help at the right moment across banking, insurance and investing, with guardrails that protect customers and keep every decision explainable.

## ADDED Requirements

### Requirement: Intervention catalog
The system SHALL choose interventions from a fixed catalog. Each entry has:
- a key and a title
- a customer-facing message
- a product line: `banking`, `insurance`, `investing` or `support`
- a default channel: `app`, `email` or `advisor`
- a trigger: a moment, a pinch point, or a sustained surplus

The catalog SHALL cover every moment except `no_clear_moment`, plus pinch points and surplus.

#### Scenario: Catalog coverage
- **WHEN** the catalog is inspected
- **THEN** there is at least one entry for each of: moving home, growing family, new job, approaching retirement, buying a car, travel abroad, financial stress, pinch point, and surplus

### Requirement: Guardrail policy
The system SHALL assign each candidate intervention a status: `delivered` (sent automatically), `review` (waiting for an advisor), `held` (not sent), or `dismissed`. It SHALL apply these rules in order:
1. If stress is at least 0.6, only `support` interventions are allowed. They go to `review` through the `advisor` channel, and all sales interventions are `held`.
2. Sales interventions for a customer without marketing consent are `held`.
3. If receptiveness is 0 (not now), moment interventions are `held`.
4. If the moment's confidence is below the customer's proactivity threshold, moment interventions are `held`. The thresholds are: `minimal` means moment interventions are never sent; `balanced` requires 0.75; `proactive` requires 0.5.
5. Moment interventions with a confidence between 0.5 and 0.75 go to `review`.
6. Everything else is `delivered`.

#### Scenario: Stressed customer gets support, not sales
- **WHEN** the financial-stress story customer is analyzed
- **THEN** a `support` intervention is in `review` through the `advisor` channel, and no `banking`, `insurance` or `investing` intervention is `delivered`

#### Scenario: Confident moment is delivered
- **WHEN** a consenting, receptive customer with `balanced` proactivity has `moving_home` at a confidence of 0.85 and a stress of 0.1
- **THEN** the moving-home intervention is `delivered` through its default channel

### Requirement: Explainable decisions
Every intervention SHALL carry a list of human-readable reasons naming the signals, probabilities and rules that led to its status.

#### Scenario: Why am I seeing this
- **WHEN** a delivered intervention is shown to the customer
- **THEN** its reasons include the detected moment with its confidence, and the pinch point or signal it responds to

### Requirement: Timing
Pinch-point interventions SHALL have a delivery date 21 days before the first day of the pinch month, or today if that date has passed. Moment interventions SHALL be dated today.

#### Scenario: Acting before the pinch
- **WHEN** a pinch point is forecast for 2027-03
- **THEN** the related intervention's delivery date is 2027-02-08

### Requirement: Advisor decisions and customer feedback
An advisor SHALL be able to approve an intervention in `review` (it becomes `delivered`) or dismiss it (it becomes `dismissed`). A customer SHALL be able to mark a delivered intervention as `helpful` or `not_relevant`. Marking it `not_relevant` removes it from their view.

#### Scenario: Advisor approves
- **WHEN** an advisor approves an intervention in `review`
- **THEN** its status becomes `delivered` and it appears in the customer's app

#### Scenario: Customer dismisses
- **WHEN** a customer marks a card `not_relevant`
- **THEN** the card no longer appears in their app, and the feedback is visible to advisors

### Requirement: Re-evaluation is incremental
The system SHALL re-analyze a customer only when they get a new signal or change their proactivity. Each analysis SHALL record its AI token usage so the cost per analysis can be reported.

#### Scenario: Unchanged customer is not re-analyzed
- **WHEN** the customer list is loaded repeatedly without new signals
- **THEN** no new moment detection runs
