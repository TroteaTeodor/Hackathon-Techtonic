"""Transaction insights: a category for every transaction, recurring detection, subscriptions and spend by category.

Deterministic and explainable (like the twin): merchant and keyword rules, no AI. The first matching rule wins.
"""

import re
from collections import defaultdict
from datetime import timedelta
from statistics import median

from app import schemas
from app.twin import RECURRING_MAX_GAP_DAYS, month_key, recurring_keys

CATEGORY_LABELS: dict[str, str] = {
    "income": "Income",
    "housing": "Housing",
    "energy": "Energy & water",
    "telecom": "Phone & internet",
    "groceries": "Groceries",
    "transport": "Transport",
    "subscriptions": "Subscriptions",
    "entertainment": "Entertainment",
    "dining": "Eating out",
    "shopping": "Shopping",
    "health": "Health",
    "insurance": "Insurance",
    "travel": "Travel",
    "family": "Family & children",
    "loans": "Loans & credit",
    "fees": "Bank fees & interest",
    "savings": "Savings & investing",
    "other": "Other",
}

# (category, patterns): matched against the lower-cased description; first match wins, so specific rules go first.
RULES: list[tuple[str, tuple[str, ...]]] = [
    ("fees", ("overdraft interest", "bank fee", "collection agency", "returned direct debit", "bailiff", "gerechtsdeurwaarder")),
    ("loans", ("home loan", "mortgage", "car loan", "klarna", "cofidis", "buy way", "in3", "instalment", "cash advance", "mini loan")),
    ("income", ("salary", "holiday pay", "student job", "groeipakket", "child benefit", "pension payment", "refund", "payout")),
    ("subscriptions", ("netflix", "spotify", "disney+", "streamz", "youtube premium", "icloud", "amazon prime", "prime video",
                       "xbox", "playstation plus", "de standaard", "de tijd", "basic-fit", "jims fitness", "chatgpt", "adobe",
                       "subscription", "abonnement")),
    ("savings", ("pension savings", "savings", "investment", "bolero", "degiro")),
    ("insurance", ("insurance", "verzekering", "assurance", "mutualiteit", "mutualité")),
    ("housing", ("rent", "huur", "loyer", "notary", "notaris", "notaire", "rental guarantee", "syndic", "movers")),
    ("energy", ("energy", "engie", "luminus", "fluvius", "eneco", "water", "sibelga", "vivaqua", "de watergroep")),
    ("telecom", ("telecom", "proximus", "telenet", "orange", "mobile vikings", "scarlet", "internet", "esim")),
    ("groceries", ("groceries", "colruyt", "delhaize", "aldi", "lidl", "carrefour", "albert heijn", "okay ", "spar ")),
    ("transport", ("nmbs", "sncb", "de lijn", "stib", "fuel", "totalenergies", "q8", "shell", "parking", "cambio", "blue-bike")),
    ("travel", ("brussels airlines", "ryanair", "klm", "tui", "transavia", "booking.com", "airbnb", "hotel", "eurostar")),
    ("dining", ("restaurant", "deliveroo", "uber eats", "takeaway", "café", "cafe", "brasserie", "frituur", "pizza")),
    ("entertainment", ("kinepolis", "ticketmaster", "concert", "festival", "museum", "bowling", "steam")),
    ("family", ("dreambaby", "prenatal", "kruidvat — baby", "kind en gezin", "creche", "childcare", "school")),
    ("health", ("apotheek", "pharmacy", "pharmacie", "doctor", "dokter", "dentist", "tandarts", "hospital", "optician")),
    ("shopping", ("fnac", "zalando", "ikea", "coolblue", "bol.com", "mediamarkt", "kruidvat", "hema", "action", "decathlon",
                  "primark", "zara", "amazon", "card payment")),
]

# Word-start matching, so "rent" doesn't hit "current" or "parental".
_PATTERNS = [(c, [re.compile(r"(?<![a-z0-9])" + re.escape(p)) for p in ps]) for c, ps in RULES]

SUBSCRIPTION_MAX_AMOUNT = 150
ONE_OFF_EXCLUDED_FROM_SPENDING = 1000  # a notary deposit or a car deposit isn't "monthly spending"
PRICE_CHANGE_MIN_EUR = 0.5


def classify(description: str, amount: float | None) -> str:
    text = description.lower()
    for category, patterns in _PATTERNS:
        if any(p.search(text) for p in patterns):
            return category
    if amount is not None and amount > 0:
        return "income"
    return "other"


def merchant(description: str) -> str:
    """'Streaming — Netflix' -> 'Netflix': descriptions read 'What — Merchant', like the app shows them."""
    parts = re.split(r"\s+[—–]\s+", description, maxsplit=1)
    return parts[-1].strip()


def _norm(description: str) -> str:
    return " ".join(description.lower().split())


def signal_views(signals) -> list[schemas.Signal]:
    """API view of signals with their category and whether the charge repeats (monthly or yearly)."""
    repeating = recurring_keys(signals)
    return [
        schemas.Signal(
            id=s.id, date=s.date, description=s.description, amount=s.amount, kind=s.kind,
            category=classify(s.description, s.amount) if s.kind == "transaction" else None,
            recurring=s.kind == "transaction" and _norm(s.description) in repeating,
        )
        for s in signals
    ]


def subscriptions(signals) -> list[schemas.Subscription]:
    """Repeating fixed charges from subscription merchants, with the latest price and any recent price change."""
    tx = [s for s in signals if s.kind == "transaction" and (s.amount or 0) < 0]
    if not tx:
        return []
    latest = max(s.date for s in signals)
    groups: dict[str, list] = defaultdict(list)
    for s in tx:
        if classify(s.description, s.amount) == "subscriptions" and -s.amount <= SUBSCRIPTION_MAX_AMOUNT:
            groups[merchant(s.description).lower()].append(s)

    out = []
    for charges in groups.values():
        charges.sort(key=lambda s: s.date)
        months = {month_key(s.date) for s in charges}
        if len(months) < 3 or (latest - charges[-1].date).days > RECURRING_MAX_GAP_DAYS:
            continue  # not (or no longer) a running subscription
        last = round(-charges[-1].amount, 2)
        previous = next((round(-c.amount, 2) for c in reversed(charges[:-1]) if abs(-c.amount - last) >= PRICE_CHANGE_MIN_EUR), None)
        changed_recently = previous is not None and any(
            abs(-c.amount - previous) < PRICE_CHANGE_MIN_EUR and (latest - c.date).days <= 100 for c in charges
        )
        out.append(schemas.Subscription(
            name=merchant(charges[-1].description),
            monthly_amount=last,
            yearly_amount=round(last * 12, 2),
            since=min(months),
            last_charged=charges[-1].date,
            price_change=schemas.PriceChange(before=previous, after=last) if changed_recently else None,
        ))
    return sorted(out, key=lambda s: -s.monthly_amount)


def spending(signals, months: int = 3) -> list[schemas.CategorySpend]:
    """Average monthly spend per category over the last `months` months, largest first.

    Large one-off payments (≥ €1,000 and not repeating, like a notary deposit) are left out: they are events,
    not monthly spending, and the twin and the moment cards already handle them.
    """
    tx = [s for s in signals if s.kind == "transaction" and (s.amount or 0) < 0]
    if not tx:
        return []
    latest = max(s.date for s in signals)
    since = latest - timedelta(days=30 * months)
    repeating = recurring_keys(signals)
    totals: dict[str, float] = defaultdict(float)
    recurring_totals: dict[str, float] = defaultdict(float)
    for s in tx:
        if s.date <= since:
            continue
        repeats = _norm(s.description) in repeating
        if not repeats and -s.amount >= ONE_OFF_EXCLUDED_FROM_SPENDING:
            continue
        category = classify(s.description, s.amount)
        if category == "income":
            continue
        totals[category] += -s.amount
        if repeats:
            recurring_totals[category] += -s.amount
    grand = sum(totals.values()) or 1.0
    rows = [
        schemas.CategorySpend(
            category=c, label=CATEGORY_LABELS[c], monthly_average=round(v / months, 2),
            share=round(v / grand, 3), recurring_share=round(recurring_totals[c] / v, 3) if v else 0.0,
        )
        for c, v in totals.items()
    ]
    return sorted(rows, key=lambda r: -r.monthly_average)


def monthly_median_income(signals) -> float:
    incomes = defaultdict(float)
    for s in signals:
        if s.kind == "transaction" and (s.amount or 0) > 0 and classify(s.description, s.amount) == "income":
            incomes[month_key(s.date)] += s.amount
    return median(incomes.values()) if incomes else 0.0
