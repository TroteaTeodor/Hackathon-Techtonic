"""Deterministic keyword/amount rules. Also used for the generated population (no API cost)."""

from app.detection import LABELS, Detection
from app.schemas import MOMENT_KEYS

KEYWORDS: dict[str, dict[str, float]] = {
    "moving_home": {
        "notary": 3, "notaris": 3, "immoweb": 1.5, "zimmo": 1.5, "mortgage": 1.5,
        "home insurance": 1, "moving company": 1.5, "real estate": 1,
    },
    "growing_family": {
        "baby": 2, "prenatal": 2, "maternity": 2, "pregnan": 2, "parental leave": 1.5,
        "birth": 2, "child savings": 1.5, "stroller": 1.5, "childcare": 1.5, "creche": 1.5,
    },
    "new_job": {
        "first salary": 2, "new employer": 2, "updated employer": 2, "employment contract": 2,
        "salary account switching": 1.5,
    },
    "approaching_retirement": {"pension": 2, "retire": 2},
    "buying_car": {
        "car loan": 2, "autoscout": 1.5, "dealer": 1.5, "car insurance quote": 1.5, "test drive": 1.5,
    },
    "travel_abroad": {
        "brussels airlines": 1.5, "ryanair": 1.5, "booking.com": 1.5, "airbnb": 1,
        "travel insurance": 1.5, "passport": 1, "abroad": 1,
    },
    "financial_stress": {
        "returned direct debit": 2, "payment reminder": 2, "collection agency": 2.5,
        "overdraft": 2, "missed": 2, "cash advance": 1.5, "payment plan": 1.5,
    },
}

# Prior weight so that a customer without matching signals lands on no_clear_moment.
BASE_SCORE = 0.05
NO_MOMENT_SCORE = 1.0


def _normalize(scores: dict[str, float]) -> dict[str, float]:
    total = sum(scores.values())
    probs = {k: round(v / total, 3) for k, v in scores.items()}
    top = max(probs, key=probs.get)
    probs[top] = round(probs[top] + 1 - sum(probs.values()), 3)
    return probs


def detect(customer, signals) -> Detection:
    scores = {k: BASE_SCORE for k in MOMENT_KEYS}
    scores["no_clear_moment"] = NO_MOMENT_SCORE
    matched: dict[str, list] = {k: [] for k in KEYWORDS}
    stress_hits = 0

    for signal in signals:
        text = signal.description.lower()
        for moment, words in KEYWORDS.items():
            weight = sum(w for word, w in words.items() if word in text)
            if weight:
                scores[moment] += weight
                matched[moment].append(signal)
                if moment == "financial_stress":
                    stress_hits += 1

    probs = _normalize(scores)
    key = max(probs, key=probs.get)
    stress = round(1 - 0.55**stress_hits, 2)

    evidence = matched.get(key, [])
    # Customers who search, use the app or contact us about their moment are actively looking.
    active = any(s.kind in ("search", "app_event", "contact") for s in evidence)
    receptiveness = 2 if active else 1

    if evidence:
        names = "; ".join(s.description for s in evidence[:3])
        rationale = f"{LABELS[key]}: based on {names}."
    else:
        rationale = "No signals point to a specific life change; activity looks routine."

    return Detection(
        key=key,
        confidence=probs[key],
        probabilities=probs,
        stress=stress,
        receptiveness=receptiveness,
        rationale=rationale,
        source="rules",
        matched=[s.description for s in evidence],
    )
