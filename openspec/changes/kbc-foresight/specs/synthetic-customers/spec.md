# Spec Delta

## Purpose

Provides a fake but realistic customer population, with transaction and app signals, so the Foresight proof of concept can be demonstrated without any real personal data.

## ADDED Requirements

### Requirement: Story customers with scripted life events
The system SHALL seed a fixed set of story customers. Each has 12 months of transaction history and recent signals that express one scripted situation. The set SHALL include at least: moving home, growing family, first job, approaching retirement, financial stress, buying a car, and one routine customer with no life event.

#### Scenario: Seeding a fresh database
- **WHEN** the backend starts against an empty database
- **THEN** the story customers exist, each with a salary or income stream, recurring costs, and recent signals matching their scripted situation

#### Scenario: Seeding is idempotent
- **WHEN** the backend restarts against a database that is already seeded
- **THEN** no duplicate customers or signals are created

### Requirement: Generated population for scale
The system SHALL generate a background population of at least 200 customers from randomized templates using a fixed random seed, so repeated runs produce the same population.

#### Scenario: Deterministic population
- **WHEN** the database is reset and seeded twice
- **THEN** both runs produce the same number of customers with the same names and moment mix

### Requirement: Signals are typed and dated
Every signal SHALL have a date, a kind (`transaction`, `app_event`, `search` or `contact`) and a description. Transactions SHALL also have a signed amount in euros, negative for money going out.

#### Scenario: Reading a customer's signals
- **WHEN** an advisor opens a customer
- **THEN** each signal shows its date, kind, description, and amount when it is a transaction

### Requirement: Injecting a signal
An advisor SHALL be able to add a new signal to a customer. Adding one SHALL immediately re-run moment detection, the twin and interventions for that customer.

#### Scenario: Injected signal changes the picture
- **WHEN** an advisor injects the transaction "Notary deposit — Notaris Peeters" of -€15,000 for the routine customer
- **THEN** the response contains the customer's updated moment, twin and interventions reflecting the new signal

#### Scenario: Invalid signal is rejected
- **WHEN** an injected signal has an unknown kind, an empty description, or a description over 200 characters
- **THEN** the request fails with a 422 validation error and nothing is stored

### Requirement: No real personal data
Seeded and generated data SHALL be fictitious. It SHALL NOT contain real account numbers, national register numbers, or real people's contact details.

#### Scenario: Reviewing seed data
- **WHEN** the seed definitions are inspected
- **THEN** names, IBAN-like values and contact fields are clearly synthetic (for example `BE00 0000 …`)
