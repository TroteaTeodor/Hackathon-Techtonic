# Spec Delta

## Purpose

Projects each customer's finances over the next 12 months, so KBC can see how a life moment will affect them and act before a shortfall occurs.

## ADDED Requirements

### Requirement: Twelve-month forecast
The system SHALL produce, for each customer, a forecast of the next 12 calendar months, starting with the month after the latest signal. Each month SHALL include total income, total expenses, the projected end-of-month balance, and the events that make up those totals. Each event has a label, a signed amount, and a source: `recurring`, `scheduled` or `moment`.

#### Scenario: Forecast shape
- **WHEN** a customer's twin is requested
- **THEN** it contains the starting balance and exactly 12 consecutive months, each with income, expenses, balance and events

### Requirement: Forecast from observed history
The system SHALL treat income and costs seen in at least 3 of the last 12 months with a similar amount as recurring, and SHALL project them monthly. Payments seen once a year (for example insurance premiums or taxes) SHALL be projected in the same calendar month of the coming year as `scheduled` events.

#### Scenario: Yearly insurance premium
- **WHEN** a customer paid a car insurance premium of -€640 in March of last year
- **THEN** the forecast includes a `scheduled` event of -€640 in the coming March

### Requirement: Moment adjustments
The detected moment SHALL change the forecast using documented adjustments for each moment, marked with source `moment`. For example:
- `moving_home` adds notary and moving costs, and replaces rent with a mortgage payment
- `growing_family` adds childcare costs and child benefit
- `approaching_retirement` reduces income from the retirement month
- `buying_car` adds a one-off purchase or a loan payment

Adjustments SHALL apply only when the moment's confidence is at least 0.5.

#### Scenario: Moving home changes the future
- **WHEN** the moving-home customer is detected with a confidence of at least 0.5
- **THEN** their forecast contains `moment` events for the notary and moving costs and for the mortgage payment, and the balance line differs from the forecast without adjustments

#### Scenario: Low confidence does not change the forecast
- **WHEN** a moment is detected with a confidence below 0.5
- **THEN** the forecast contains no `moment` events

### Requirement: Pinch points
The system SHALL flag every forecast month whose end balance falls below a safety buffer of €250 as a pinch point. Each pinch point has the month, the projected balance, and a human-readable reason naming the largest contributing expense.

#### Scenario: Balance dips
- **WHEN** a projected March balance is -€1,200 because of notary fees
- **THEN** March is a pinch point whose reason mentions the notary fees
