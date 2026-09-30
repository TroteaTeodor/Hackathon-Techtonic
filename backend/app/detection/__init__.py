"""Life-moment detection: Gemini when configured, deterministic rules otherwise (or on any failure)."""

from dataclasses import dataclass, field

LABELS = {
    "moving_home": "Moving home",
    "growing_family": "Growing family",
    "new_job": "New job",
    "approaching_retirement": "Approaching retirement",
    "buying_car": "Buying a car",
    "travel_abroad": "Travelling abroad",
    "financial_stress": "Financial stress",
    "no_clear_moment": "No clear moment",
}

# Only the most recent signals are used as detection input.
MAX_SIGNALS = 40


@dataclass
class Detection:
    key: str
    confidence: float
    probabilities: dict[str, float]
    stress: float
    receptiveness: int
    rationale: str
    source: str
    input_tokens: int = 0
    output_tokens: int = 0
    matched: list[str] = field(default_factory=list)
    cost_usd: float | None = None  # actual provider cost when reported (Jev)


def normalize(scores: dict[str, float]) -> dict[str, float]:
    """Scale to a distribution rounded to 3 decimals; the rounding residual goes to the top key."""
    total = sum(scores.values()) or 1.0
    probs = {k: round(v / total, 3) for k, v in scores.items()}
    top = max(probs, key=probs.get)
    probs[top] = round(probs[top] + 1 - sum(probs.values()), 3)
    return probs


def recent(signals, limit: int = MAX_SIGNALS):
    return sorted(signals, key=lambda s: (s.date, s.id or 0), reverse=True)[:limit]


def detect(customer, signals, use_ai: bool = True) -> Detection:
    from app.detection import gemini, rules

    latest = recent(signals)
    if use_ai and gemini.is_configured():
        result = gemini.detect(customer, latest)
        if result is not None:
            return result
    return rules.detect(customer, latest)
