# Spec Delta

## Purpose

Recognizes what is changing in a customer's life from their signals, with enough confidence information for the system to decide whether, when and how to act.

## ADDED Requirements

### Requirement: Moment detection output
For a customer, the system SHALL produce a moment assessment containing:
- one moment key from the fixed set `moving_home`, `growing_family`, `new_job`, `approaching_retirement`, `buying_car`, `travel_abroad`, `financial_stress`, `no_clear_moment`
- a confidence between 0 and 1
- a probability for every key, summing to 1 within a 0.01 tolerance
- a stress score between 0 and 1
- a receptiveness level: 0 = not now, 1 = open to a light nudge, 2 = actively looking for help
- a one-sentence rationale
- the source (`jev`, `gemini`, `rules` or `customer`)
- the time of analysis

#### Scenario: Story customer is recognized
- **WHEN** the moving-home story customer is analyzed
- **THEN** the moment is `moving_home` with a confidence of at least 0.6, and the rationale refers to the signals behind it

#### Scenario: Routine customer is not over-interpreted
- **WHEN** the routine story customer is analyzed
- **THEN** the moment is `no_clear_moment`, or any other moment has a confidence below 0.5

### Requirement: AI-based detection
When AI credentials are configured, the system SHALL detect moments with a cascade:
- Jev (a calibrated decision model) answers first.
- When Jev's confidence is below the escalation threshold (default 0.75), or Jev fails, the system SHALL use Gemini.
- Both models SHALL receive only the customer's profile and their most recent signals (at most 40). The system SHALL validate every structured response before using it.
- The assessment SHALL record which model produced it (`jev`, `gemini`, `rules` or `customer`).

#### Scenario: Confident Jev answer
- **WHEN** Jev returns a moment with a confidence of at least the escalation threshold
- **THEN** that assessment is used with source `jev`, and Gemini is not called

#### Scenario: Unsure Jev escalates to Gemini
- **WHEN** Jev's confidence is below the escalation threshold, and Gemini returns a valid assessment
- **THEN** the Gemini assessment is used with source `gemini`, and its rationale notes that it was escalated from Jev

#### Scenario: Malformed AI response
- **WHEN** Gemini returns a response that is missing fields or uses an unknown moment key
- **THEN** the system uses Jev's answer if there was one, or otherwise the rule-based result, and records its source

### Requirement: Rule-based fallback
The system SHALL produce a moment assessment without any AI service, using deterministic rules over signal descriptions and amounts. It SHALL do so whenever no AI credentials are configured, or every AI call in the cascade fails or takes longer than 10 seconds.

#### Scenario: No AI credentials configured
- **WHEN** the backend runs without Jev or Vertex AI credentials and a customer is analyzed
- **THEN** a complete assessment is returned with source `rules`, and no request is made to an external service

### Requirement: Detection stays within the customer's data
The input sent to the AI service SHALL contain only the analyzed customer's own synthetic data. It SHALL NOT contain other customers' data, credentials or secrets.

#### Scenario: Prompt content
- **WHEN** a detection request is built for a customer
- **THEN** it includes only that customer's profile fields and signals, plus the fixed instructions
