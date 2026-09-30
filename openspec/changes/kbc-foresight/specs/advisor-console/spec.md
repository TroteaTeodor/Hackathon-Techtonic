# Spec Delta

## Purpose

Gives KBC staff a console to see which customers are in which moment, to review sensitive or uncertain actions, to demonstrate live adaptation, and to show how the approach scales to 2.3M customers.

## ADDED Requirements

### Requirement: Customer list
The console SHALL list customers with their name, age, city, moment with confidence, stress indicator, next pinch month, and the number of interventions waiting for review. It SHALL be filterable by moment and by "needs review".

#### Scenario: Filter to review queue
- **WHEN** the advisor selects "needs review"
- **THEN** only customers with at least one intervention in `review` are listed

### Requirement: Customer detail
The console SHALL show, for one customer:
- their profile, consent and proactivity
- a signal timeline
- the moment with all probabilities as bars, plus stress, receptiveness, rationale and source
- the 12-month twin chart with `moment` events visually distinguished
- all interventions with status, channel, delivery date, reasons and customer feedback

#### Scenario: Advisor opens Sara
- **WHEN** the advisor opens Sara's detail
- **THEN** the probability bars, twin chart and interventions with reasons are visible

### Requirement: Inject signal for live demo
The detail view SHALL offer preset signals (for example a notary deposit, a baby-store purchase, or a missed loan payment) and a free-form form to inject a signal. It SHALL then show the updated moment, twin and interventions without a page reload.

#### Scenario: Live adaptation
- **WHEN** the advisor injects the "notary deposit" preset for the routine customer
- **THEN** within a few seconds the moment, twin and interventions update on screen

### Requirement: Review decisions
The console SHALL let the advisor approve or dismiss interventions in `review`.

#### Scenario: Approve from console
- **WHEN** the advisor approves a review item
- **THEN** its status shows `delivered`

### Requirement: Scale view
The console SHALL show:
- population size
- moment distribution
- interventions by status, including the share handled automatically versus by advisors
- average AI cost per analysis
- a projected daily cost for 2.3M customers at a stated daily re-evaluation rate, with the assumptions shown

#### Scenario: Projection shown with assumptions
- **WHEN** the advisor opens the scale view
- **THEN** it shows the projected daily and monthly cost for 2.3M customers, together with the re-evaluation rate and the price per token it assumes

### Requirement: Works with mock data
The frontend SHALL be able to run entirely on bundled mock data matching the API contract, controlled by a configuration flag, so it can be developed and demoed without the backend.

#### Scenario: Mock mode
- **WHEN** the frontend runs with `NEXT_PUBLIC_USE_MOCKS=true` and no backend
- **THEN** login, the customer app, the console and the scale view all render with fixture data
