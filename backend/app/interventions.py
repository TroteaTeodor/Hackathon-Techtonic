"""Intervention catalog and the guardrail policy (ordered rules, see specs/proactive-interventions)."""

import calendar
import re
from datetime import date, timedelta

from app.detection import LABELS
from app.twin import euro

# trigger: a moment key, "pinch", "pinch_support" or "surplus".
CATALOG: dict[str, dict] = {
    # Moment cards name what we noticed, ask instead of assuming, and offer one direct next step (cta).
    "moving_home_bundle": dict(
        trigger="moving_home", line="banking", channel="app", title="Moving home?",
        message="{noticed} Are you moving? If so, congratulations! Your mortgage options and a pre-approval "
        "in 10 minutes are ready for you here.",
        cta="See my mortgage options",
    ),
    "moving_home_insurance": dict(
        trigger="moving_home", line="insurance", channel="app", title="Home insurance for your new place",
        message="If you're moving, you'll need fire and home insurance for the new address: it's required for a "
        "mortgage. Get covered from here in two minutes, from the day you sign.",
        cta="Get home insurance",
    ),
    "growing_family_savings": dict(
        trigger="growing_family", line="investing", channel="app", title="A little one on the way?",
        message="{noticed} Is your family growing? Congratulations! Open a child savings account in one tap "
        "and see how childcare and child benefit change your budget.",
        cta="Open a child savings account",
    ),
    "growing_family_cover": dict(
        trigger="growing_family", line="insurance", channel="app", title="Cover for a growing family",
        message="With a new family member, check that your hospitalisation and life insurance cover everyone "
        "from day one. Review it from here.",
        cta="Review my family cover",
    ),
    "new_job_salary": dict(
        trigger="new_job", line="banking", channel="app", title="Started a new job?",
        message="{noticed} Did you start a new job? Congrats! Split each salary automatically into spending, "
        "savings and a safety buffer.",
        cta="Set up automatic saving",
    ),
    "retirement_plan": dict(
        trigger="approaching_retirement", line="investing", channel="advisor", title="Thinking about retiring?",
        message="{noticed} Are you planning your retirement? Your income will change, so book a free pension "
        "planning session to see how to bridge the gap.",
        cta="Book a pension session",
    ),
    "buying_car_loan": dict(
        trigger="buying_car", line="banking", channel="app", title="Looking for a car?",
        message="{noticed} Are you shopping for a car? Compare a car loan with paying cash, based on your own "
        "12-month forecast.",
        cta="Compare loan vs cash",
    ),
    "buying_car_insurance": dict(
        trigger="buying_car", line="insurance", channel="app", title="Car insurance before you drive",
        message="If you're buying a car, get your insurance quote now so there's no gap on the day you pick it up.",
        cta="Get a car insurance quote",
    ),
    "travel_cover": dict(
        trigger="travel_abroad", line="insurance", channel="app", title="Going abroad?",
        message="{noticed} Travelling soon? Add travel insurance and enable your card for payments outside Europe.",
        cta="Add travel insurance",
    ),
    # Sensitive: never mention what we saw, just offer help.
    "stress_budget_coach": dict(
        trigger="financial_stress", line="support", channel="advisor", title="Let's get your budget back on track",
        message="{first_name}, an advisor can help you set up a payment plan and a budget, free of charge "
        "and with no obligation.",
        cta="Talk to an advisor",
    ),
    "pinch_point_bridge": dict(
        trigger="pinch", line="banking", channel="app", title="Heads-up for {month_name}",
        message="Your balance is projected to reach about {balance} in {month_name}. Move money from savings "
        "now, or set up a short bridge loan in one tap.",
        cta="Move money from savings",
    ),
    "pinch_point_support": dict(
        trigger="pinch_support", line="support", channel="advisor", title="A tight month is coming",
        message="Your balance may drop to {balance} in {month_name}. An advisor can help you spread "
        "payments before it happens.",
        cta="Talk to an advisor",
    ),
    "subscription_review": dict(
        trigger="subscriptions", line="support", channel="app", title="Your subscriptions: {total} a month",
        message="{first_name}, you pay {total} a month ({yearly} a year) for {count} subscriptions.{change} "
        "Review them in one tap and cancel what you no longer use.",
        cta="Review my subscriptions",
    ),
    "surplus_invest": dict(
        trigger="surplus", line="investing", channel="app", title="Put idle cash to work",
        message="{first_name}, your balance stays well above what you need every month. Start a monthly "
        "investment plan from €50 and keep a safety buffer.",
        cta="Start investing from €50",
    ),
}


def noticed(signal) -> str:
    """'We noticed …' sentence for the signal behind a moment, in the customer's terms."""
    if signal is None:
        return "Something in your recent activity suggests a change."
    when = f"{signal.date.day} {calendar.month_name[signal.date.month]}"
    desc = signal.description
    if signal.kind == "transaction" and signal.amount is not None:
        who = re.split(r"\s+[—–-]\s+", desc, maxsplit=1)[-1] if " — " in desc else desc
        if signal.amount < 0:
            return f"We noticed a {euro(-signal.amount)} payment to {who} on {when}."
        return f"We noticed a {euro(signal.amount)} payment from {who} on {when}."
    if signal.kind == "search":
        return f"We noticed you searched for “{desc}”."
    if signal.kind == "app_event":
        return f"We noticed you {desc[0].lower() + desc[1:]}."
    return f"Thanks for your question (“{desc}”)."


STRESS_THRESHOLD = 0.6
REVIEW_BELOW = 0.75
PROACTIVITY_THRESHOLD = {"balanced": 0.75, "proactive": 0.5}
PINCH_LEAD_DAYS = 21
SURPLUS_MULTIPLE = 5
SUBSCRIPTION_SHARE_OF_INCOME = 0.03  # suggest a check-up above 3% of income, 4+ subscriptions, or a price rise
SUBSCRIPTION_MIN_COUNT = 4


def pct(value: float) -> str:
    return f"{round(value * 100)}%"


def month_label(month: str) -> str:
    return f"{calendar.month_name[int(month[5:])]} {month[:4]}"


def pinch_delivery(month: str, today: date) -> date:
    first = date(int(month[:4]), int(month[5:]), 1)
    return max(today, first - timedelta(days=PINCH_LEAD_DAYS))


def _render(key: str, customer, **extra) -> dict:
    entry = CATALOG[key]
    fields = {"first_name": customer.first_name, "noticed": "", **extra}
    return {
        "key": key,
        "title": entry["title"].format(**fields),
        "message": " ".join(entry["message"].format(**fields).split()),
        "line": entry["line"],
        "channel": entry["channel"],
        "cta": entry.get("cta"),
    }


def _pinch_fields(pinch) -> dict:
    return {"month_name": calendar.month_name[int(pinch.month[5:])], "balance": euro(pinch.balance)}


def _subscription_review(customer, subs, income: float):
    """A service message (not sales): shown when subscriptions add up, or one of them just got more expensive."""
    if not subs:
        return None
    total = sum(s.monthly_amount for s in subs)
    rises = [s for s in subs if s.price_change and s.price_change.after > s.price_change.before]
    if not (rises or len(subs) >= SUBSCRIPTION_MIN_COUNT or (income and total >= SUBSCRIPTION_SHARE_OF_INCOME * income)):
        return None
    change = ""
    if rises:
        r = rises[0]
        change = f" {r.name} went up from €{r.price_change.before:.2f} to €{r.price_change.after:.2f}."
    fields = {"total": f"€{total:.2f}", "yearly": euro(total * 12), "count": len(subs), "change": change}
    reasons = [f"{len(subs)} recurring subscriptions found: " + ", ".join(f"{s.name} €{s.monthly_amount:.2f}" for s in subs[:5])]
    if rises:
        reasons.append(f"Price rise detected: {rises[0].name} €{rises[0].price_change.before:.2f} → €{rises[0].price_change.after:.2f}")
    if income:
        reasons.append(f"Subscriptions are {total / income:.1%} of monthly income")
    reasons.append("A service check-up, not an offer: no consent or proactivity rule applies")
    return fields, reasons


def plan(customer, detection, twin, today: date | None = None, subs=None, income: float = 0.0, signals=None) -> list[dict]:
    """Return intervention dicts (key, title, message, line, channel, status, deliver_at, reasons)."""
    today = today or date.today()
    out: list[dict] = []
    review = _subscription_review(customer, subs or [], income)
    from app.detection import rules  # local import: rules imports nothing from here, but keep the module light
    moment_signal = rules.evidence(detection.key, sorted(signals or [], key=lambda x: x.date, reverse=True)[:40])
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
        if review:  # cutting subscriptions is support too; the advisor brings it up
            add("subscription_review", "review", review[1] + [guard], **review[0])
        return out

    # Pinch-point warnings are a service, not a sales message: they skip the consent and proactivity rules.
    if pinch:
        add("pinch_point_bridge", "delivered", pinch_reasons, pinch_delivery(pinch.month, today), **_pinch_fields(pinch))
    if review:  # a service message like the pinch warning
        add("subscription_review", "delivered", review[1], **review[0])

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
            add(key, status, [moment_reason, evidence, why], noticed=noticed(moment_signal))

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
