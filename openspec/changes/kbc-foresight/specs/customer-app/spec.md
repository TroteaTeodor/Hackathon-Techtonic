# Spec Delta

## Purpose

Shows customers, in a mobile-app style view, what KBC understands about their situation and their next 12 months, and the help KBC offers at the right moment, with the customer in control.

## ADDED Requirements

### Requirement: Your next 12 months
The customer view SHALL show:
- the customer's current balance
- a 12-month forecast chart of the projected balance, with pinch points marked
- the list of upcoming events for the next 3 months

#### Scenario: Customer opens the app
- **WHEN** a logged-in customer opens `/app`
- **THEN** they see their name, balance, the 12-month chart with pinch points highlighted, and their upcoming events

### Requirement: Detected moment, phrased for the customer
When the customer has a moment with a confidence of at least 0.5, the view SHALL show it in friendly language (for example "Looks like you're moving home") and SHALL let the customer mark it as wrong.

#### Scenario: Moment banner
- **WHEN** Sara's moment is `moving_home` at 0.87
- **THEN** a banner says she seems to be moving home and offers a "Not right" control

### Requirement: Proactive cards with reasons
The view SHALL show only `delivered` interventions, as cards with a title, message, product line and delivery date. Each card SHALL have a "Why am I seeing this?" control that reveals its reasons, and controls to mark it `helpful` or `not_relevant`.

#### Scenario: Why am I seeing this
- **WHEN** the customer opens "Why am I seeing this?" on a card
- **THEN** the card's reasons are shown

#### Scenario: Only delivered cards
- **WHEN** a customer has interventions in `review`, `held` and `delivered`
- **THEN** only the `delivered` ones appear

### Requirement: Proactivity control
The view SHALL let the customer choose how proactive KBC may be: `minimal`, `balanced` or `proactive`. The view SHALL refresh with the resulting interventions.

#### Scenario: Customer turns proactivity down
- **WHEN** a customer switches from `balanced` to `minimal`
- **THEN** moment-based sales cards disappear, and pinch-point and support cards remain

### Requirement: Works on a phone-sized screen
The customer view SHALL be usable at 375px width without horizontal scrolling.

#### Scenario: Narrow viewport
- **WHEN** the view is rendered at 375×812
- **THEN** all content fits the width and the chart is readable
