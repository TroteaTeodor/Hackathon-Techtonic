"""Financial twin: a deterministic 12-month cash-flow forecast. No AI, so every number is explainable."""

import re
from collections import defaultdict
from datetime import date, timedelta
from statistics import median

from app.schemas import PinchPoint, Twin, TwinEvent, TwinMonth

BUFFER = 250.0
MIN_MOMENT_CONFIDENCE = 0.5
RECURRING_MIN_MONTHS = 3
RECURRING_TOLERANCE = 0.35  # monthly totals within ±35% of the median count as "similar"
RECURRING_MAX_GAP_DAYS = 45  # must still be happening
YEARLY_MIN_AGE_DAYS = 60  # recent one-offs (a notary deposit) are not yearly payments
YEARLY_MIN_AMOUNT = 100
# A single payment is only projected as yearly when it looks periodic; other one-offs (a notary deposit,
# a car deposit, flight tickets) are not repeated.
YEARLY_HINTS = ("insurance", "premium", "tax", "holiday pay", "vakantiegeld", "subscription", "membership",
                "annual", "yearly", "contribution", "road tax", "verzekering", "assurance")


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def add_months(year: int, month: int, n: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + n
    return index // 12, index % 12 + 1


def euro(amount: float) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}€{abs(amount):,.0f}"


def _norm(description: str) -> str:
    return " ".join(description.lower().split())


def recurring_keys(signals) -> set[str]:
    """Normalised descriptions of charges that repeat (monthly, or yearly and periodic-looking)."""
    return analyse_history(signals, with_keys=True)[3]


def analyse_history(signals, with_keys: bool = False):
    """Split the last 12 months of transactions into recurring (monthly) and yearly items."""
    transactions = [s for s in signals if s.kind == "transaction" and s.amount is not None]
    latest = max((s.date for s in signals), default=date.today())
    window_start = latest - timedelta(days=365)

    per_month: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    last_seen: dict[str, date] = {}
    label: dict[str, str] = {}
    for t in transactions:
        if t.date <= window_start:
            continue
        key = _norm(t.description)
        per_month[key][month_key(t.date)] += t.amount
        if key not in last_seen or t.date >= last_seen[key]:
            last_seen[key] = t.date
            label[key] = t.description

    recurring: list[tuple[str, float]] = []
    yearly: list[tuple[str, float, int]] = []
    keys: set[str] = set()
    for key, months in per_month.items():
        totals = list(months.values())
        if len(months) >= RECURRING_MIN_MONTHS and (latest - last_seen[key]).days <= RECURRING_MAX_GAP_DAYS:
            mid = median(totals)
            similar = [v for v in totals if abs(v - mid) <= RECURRING_TOLERANCE * abs(mid)]
            if len(similar) >= RECURRING_MIN_MONTHS:
                recurring.append((label[key], round(mid, 2)))
                keys.add(key)
        elif len(months) == 1:
            (month, amount), = months.items()
            periodic = any(h in key for h in YEARLY_HINTS)
            if periodic and (latest - last_seen[key]).days >= YEARLY_MIN_AGE_DAYS and abs(amount) >= YEARLY_MIN_AMOUNT:
                yearly.append((label[key], round(amount, 2), int(month[5:])))
                keys.add(key)
    if with_keys:
        return latest, recurring, yearly, keys
    return latest, recurring, yearly


def _new_salary(signals, recurring_labels: set[str], latest: date):
    """A recent salary that isn't recurring yet (first salary at a new job)."""
    candidates = [
        s for s in signals
        if s.kind == "transaction" and (s.amount or 0) > 0 and "salary" in s.description.lower()
        and (latest - s.date).days <= RECURRING_MAX_GAP_DAYS and s.description not in recurring_labels
    ]
    return max(candidates, key=lambda s: s.date, default=None)


MORTGAGE_RATE = 0.035  # yearly, fixed, 25 years: a typical Belgian home loan for the estimate
MORTGAGE_MONTHS = 300
AFFORDABLE_SHARE = 0.33  # banks cap the repayment at about a third of net income
FEES_SHARE = 0.02  # registration duty on a first own home in Flanders
FEES_FIXED = 3500  # notary fees and mortgage deed costs
CHILD_BENEFIT = 180  # Groeipakket base amount per child per month


def _round(value: float, step: int = 10) -> float:
    return float(round(value / step) * step)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def monthly_income(recurring) -> float:
    salary = sum(a for lbl, a in recurring if a > 0 and "salary" in lbl.lower())
    return salary or sum(a for _, a in recurring if a > 0) or 2500.0


def home_purchase(recurring, signals) -> dict:
    """Estimate the purchase from the customer's own income and deposit (explained in the event labels)."""
    income = monthly_income(recurring)
    payment = _round(max(500.0, AFFORDABLE_SHARE * income))
    r = MORTGAGE_RATE / 12
    loan = payment * (1 - (1 + r) ** -MORTGAGE_MONTHS) / r
    deposits = [-s.amount for s in signals if s.kind == "transaction" and (s.amount or 0) < 0
                and any(w in s.description.lower() for w in ("notary", "notaris", "notaire"))]
    deposit = max(deposits) if deposits else 0.1 * loan
    price = loan + deposit
    return {
        "payment": payment,
        "price": _round(price, 1000),
        "fees": _round(FEES_SHARE * price + FEES_FIXED),
        "moving": _round(_clamp(0.5 * income, 800, 3000)),
    }


def moment_adjustments(key: str, index: int, recurring, signals, latest) -> tuple[list[tuple[str, float]], set[str]]:
    """Events a detected moment adds to forecast month `index` (0 = next month), plus labels it removes.

    Amounts are personal: they follow this customer's income (and deposit, for a home), so two customers in
    the same moment get different forecasts.
    """
    events: list[tuple[str, float]] = []
    removed: set[str] = set()
    income = monthly_income(recurring)
    if key == "moving_home":
        home = home_purchase(recurring, signals)
        if index == 1:
            events += [
                (f"Notary and registration fees (estimate, 2% of ~€{home['price']:,.0f} + €3,500)", -home["fees"]),
                ("Moving costs (estimate)", -home["moving"]),
            ]
        if index >= 2:
            events.append(("Mortgage payment — KBC home loan (estimate, 33% of income)", -home["payment"]))
            removed |= {lbl for lbl, _ in recurring if _norm(lbl).startswith("rent")}
    elif key == "growing_family":
        if index == 0:
            events.append(("Baby gear (estimate)", -_round(_clamp(0.4 * income, 600, 1800))))
        if index >= 3:
            events += [("Childcare (estimate, income-related)", -_round(_clamp(0.18 * income, 250, 800))),
                       ("Child benefit — Groeipakket (estimate)", CHILD_BENEFIT)]
    elif key == "new_job":
        new = _new_salary(signals, {lbl for lbl, _ in recurring}, latest)
        if new is not None:
            events.append((f"{new.description} (expected monthly)", round(new.amount, 2)))
            # The new salary replaces the previous employer's salary instead of adding to it.
            removed |= {lbl for lbl, amount in recurring if amount > 0 and "salary" in lbl.lower()}
        else:
            events.append(("Salary increase (estimate)", _round(0.1 * income)))
    elif key == "approaching_retirement":
        if index >= 5:
            salary = sum(a for lbl, a in recurring if a > 0 and "salary" in lbl.lower())
            events.append(("Pension replaces salary (estimate, -35%)", round(-0.35 * salary, 2)))
    elif key == "buying_car":
        if index == 0:
            events.append(("Car deposit (estimate)", -_round(_clamp(1.3 * income, 2000, 8000))))
        if index >= 1:
            events.append(("Car loan payment (estimate)", -_round(_clamp(0.1 * income, 150, 600))))
    elif key == "travel_abroad":
        if index == 0:
            events.append(("Trip costs (estimate)", -_round(_clamp(0.6 * income, 600, 3500))))
    return events, removed


def build_twin(balance: float, signals, moment_key: str | None = None, confidence: float | None = None) -> Twin:
    latest, recurring, yearly = analyse_history(signals)
    apply_moment = bool(moment_key) and (confidence or 0) >= MIN_MOMENT_CONFIDENCE

    months: list[TwinMonth] = []
    pinches: list[PinchPoint] = []
    running = round(balance, 2)
    for index in range(12):
        year, month = add_months(latest.year, latest.month, index + 1)
        events: list[TwinEvent] = []
        extra, removed = (
            moment_adjustments(moment_key, index, recurring, signals, latest) if apply_moment else ([], set())
        )
        for lbl, amount in recurring:
            if lbl not in removed:
                events.append(TwinEvent(label=lbl, amount=amount, kind="income" if amount > 0 else "expense", source="recurring"))
        for lbl, amount, cal_month in yearly:
            if cal_month == month:
                events.append(TwinEvent(label=lbl, amount=amount, kind="income" if amount > 0 else "expense", source="scheduled"))
        for lbl, amount in extra:
            events.append(TwinEvent(label=lbl, amount=amount, kind="income" if amount > 0 else "expense", source="moment"))

        income = round(sum(e.amount for e in events if e.amount > 0), 2)
        expenses = round(-sum(e.amount for e in events if e.amount < 0), 2)
        running = round(running + income - expenses, 2)
        label = f"{year:04d}-{month:02d}"
        months.append(TwinMonth(month=label, income=income, expenses=expenses, balance=running, events=events))

        if running < BUFFER:
            costs = [e for e in events if e.amount < 0]
            if costs:
                biggest = min(costs, key=lambda e: e.amount)
                name = re.sub(r" \(estimate[^)]*\)", "", biggest.label)
                reason = f"{name} ({euro(biggest.amount)[1:]}) will take your balance below the €250 buffer."
            else:
                reason = "Your balance stays below the €250 buffer."
            pinches.append(PinchPoint(month=label, balance=running, reason=reason))

    return Twin(start_balance=round(balance, 2), months=months, pinch_points=pinches)
