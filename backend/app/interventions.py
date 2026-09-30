"""Intervention catalog and the guardrail policy (ordered rules, see specs/proactive-interventions)."""

import calendar
from datetime import date, timedelta

from app.detection import LABELS
from app.twin import euro

# trigger: a moment key, "pinch", "pinch_support" or "surplus".
CATALOG: dict[str, dict] = {
    "moving_home_bundle": dict(
        trigger="moving_home", line="banking", channel="app", title="Your move, sorted",
        message="Congrats on the new place, {first_name}! Get your mortgage pre-approved in 10 minutes "
        "and have home insurance in place from the day you sign.",
    ),
    "moving_home_insurance": dict(
        trigger="moving_home", line="insurance", channel="app", title="Protect your new home",
        message="{first_name}, fire and home insurance is required for your mortgage. "
        "Get a quote for your new address in two minutes.",
    ),
    "growing_family_savings": dict(
        trigger="growing_family", line="investing", channel="app", title="A head start for your little one",
        message="Congratulations, {first_name}! Open a child savings account and see how childcare "
        "and child benefit change your budget.",
    ),
    "growing_family_cover": dict(
        trigger="growing_family", line="insurance", channel="app", title="Cover for a growing family",
        message="Review your hospitalisation and life insurance so your family is protected from day one.",
    ),
    "new_job_salary": dict(
        trigger="new_job", line="banking", channel="app", title="Welcome to your new job",
        message="Congrats on the new job, {first_name}! Split your salary automatically into spending, "
        "savings and a safety buffer.",
    ),
    "retirement_plan": dict(
        trigger="approaching_retirement", line="investing", channel="advisor", title="Plan your retirement income",
        message="{first_name}, your income will change when you retire. Book a pension planning session "
        "to see how to bridge the gap.",
    ),
    "buying_car_loan": dict(
        trigger="buying_car", line="banking", channel="app", title="Drive away with a clear budget",
        message="Compare a car loan with paying cash and see what fits your 12-month forecast.",
    ),
    "buying_car_insurance": dict(
        trigger="buying_car", line="insurance", channel="app", title="Car insurance before you drive",
        message="Get car insurance ready for your new car, with no gap on the day you pick it up.",
    ),
    "travel_cover": dict(
        trigger="travel_abroad", line="insurance", channel="app", title="Travel with peace of mind",
        message="Heading abroad, {first_name}? Add travel insurance and enable your card for payments outside Europe.",
    ),
    "stress_budget_coach": dict(
        trigger="financial_stress", line="support", channel="advisor", title="Let's get your budget back on track",
        message="{first_name}, an advisor can help you set up a payment plan and a budget, free of charge "
        "and with no obligation.",
    ),
    "pinch_point_bridge": dict(
        trigger="pinch", line="banking", channel="app", title="Heads-up for {month_name}",
        message="Your balance is projected to reach about {balance} in {month_name}. Move money from savings "
        "now, or set up a short bridge loan in one tap.",
    ),
    "pinch_point_support": dict(
        trigger="pinch_support", line="support", channel="advisor", title="A tight month is coming",
        message="Your balance may drop to {balance} in {month_name}. An advisor can help you spread "
        "payments before it happens.",
    ),
    "surplus_invest": dict(
        trigger="surplus", line="investing", channel="app", title="Put idle cash to work",
        message="{first_name}, your balance stays well above what you need every month. Start a monthly "
        "investment plan from €50 and keep a safety buffer.",
    ),
}

STRESS_THRESHOLD = 0.6
REVIEW_BELOW = 0.75
PROACTIVITY_THRESHOLD = {"balanced": 0.75, "proactive": 0.5}
PINCH_LEAD_DAYS = 21
SURPLUS_MULTIPLE = 5


def pct(value: float) -> str:
    return f"{round(value * 100)}%"


def month_label(month: str) -> str:
    return f"{calendar.month_name[int(month[5:])]} {month[:4]}"


def pinch_delivery(month: str, today: date) -> date:
    first = date(int(month[:4]), int(month[5:]), 1)
    return max(today, first - timedelta(days=PINCH_LEAD_DAYS))


def _render(key: str, customer, **extra) -> dict:
    entry = CATALOG[key]
    fields = {"first_name": customer.first_name, **extra}
    return {
        "key": key,
        "title": entry["title"].format(**fields),
        "message": entry["message"].format(**fields),
        "line": entry["line"],
        "channel": entry["channel"],
    }


def _pinch_fields(pinch) -> dict:
    return {"month_name": calendar.month_name[int(pinch.month[5:])], "balance": euro(pinch.balance)}


def plan(customer, detection, twin, today: date | None = None) -> list[dict]:
    """Return intervention dicts (key, title, message, line, channel, status, deliver_at, reasons)."""
    today = today or date.today()
    out: list[dict] = []
    pinch = twin.pinch_points[0] if twin.pinch_points else None
    moment_reason = f"Detected life moment: {LABELS[detection.key].lower()} ({pct(detection.confidence)} confidence)"
    evidence = f"Signals: {detection.rationale}"

    def add(key, status, reasons, deliver_at=today, **fields):
        out.append({**_render(key, customer, **fields), "status": status, "deliver_at": deliver_at, "reasons": reasons})

    pinch_reasons = []
    if pinch:
        pinch_reasons = [
            f"Forecast: balance of {euro(pinch.balance)} at the end of {month_label(pinch.month)}, below the €250 buffer",
            pinch.reason,
            "Sent 21 days before the month starts, so there is time to act",
        ]

    # Rule 1: financial stress (by score or by detected moment) -> support only, via an advisor; all sales held.
    if detection.stress >= STRESS_THRESHOLD or detection.key == "financial_stress":
        level = max(detection.stress, detection.confidence if detection.key == "financial_stress" else 0)
        guard = f"Guardrail: signs of financial difficulty ({pct(level)}), so support only, never sales"
        add("stress_budget_coach", "review", [guard, evidence, "An advisor reviews before anyone reaches out"])
        if pinch:
            add("pinch_point_support", "review", pinch_reasons + [guard],
                pinch_delivery(pinch.month, today), **_pinch_fields(pinch))
        for key, entry in CATALOG.items():
            if entry["trigger"] == detection.key and entry["line"] != "support":
                add(key, "held", [moment_reason, "Held: " + guard[len("Guardrail: "):]])
        return out

    # Pinch-point warnings are a service, not a sales message: they skip the consent and proactivity rules.
    if pinch:
        add("pinch_point_bridge", "delivered", pinch_reasons, pinch_delivery(pinch.month, today), **_pinch_fields(pinch))

    if detection.key not in ("no_clear_moment", "financial_stress"):
        threshold = PROACTIVITY_THRESHOLD.get(customer.proactivity)
        for key, entry in CATALOG.items():
            if entry["trigger"] != detection.key:
                continue
            if not customer.marketing_consent:  # rule 2
                status, why = "held", "Held: the customer hasn't given marketing consent"
            elif detection.receptiveness == 0:  # rule 3
                status, why = "held", "Held: signals suggest this isn't the right time to reach out"
            elif threshold is None:  # rule 4, minimal
                status, why = "held", "Held: the customer chose 'minimal' proactivity"
            elif detection.confidence < threshold:  # rule 4
                status, why = "held", (
                    f"Held: confidence {pct(detection.confidence)} is below the {pct(threshold)} "
                    f"needed for '{customer.proactivity}' proactivity"
                )
            elif detection.confidence < REVIEW_BELOW:  # rule 5
                status, why = "review", "Confidence is between 50% and 75%, so an advisor reviews before it is sent"
            else:  # rule 6
                status, why = "delivered", (
                    f"You allow offers and your proactivity is '{customer.proactivity}' "
                    f"(needs {pct(threshold)} confidence)"
                )
            add(key, status, [moment_reason, evidence, why])

    if not pinch and twin.months:
        lowest = min(m.balance for m in twin.months)
        avg_expenses = sum(m.expenses for m in twin.months) / len(twin.months)
        if avg_expenses > 0 and lowest >= SURPLUS_MULTIPLE * avg_expenses:
            reasons = [
                f"Forecast: balance stays above {euro(lowest)} for all 12 months "
                f"(over {int(lowest // avg_expenses)}× monthly expenses)",
                "No pinch points in the next 12 months",
            ]
            if not customer.marketing_consent:
                add("surplus_invest", "held", reasons + ["Held: the customer hasn't given marketing consent"])
            elif customer.proactivity == "minimal":
                add("surplus_invest", "held", reasons + ["Held: the customer chose 'minimal' proactivity"])
            else:
                add("surplus_invest", "delivered",
                    reasons + [f"You allow offers and your proactivity is '{customer.proactivity}'"])
    return out
