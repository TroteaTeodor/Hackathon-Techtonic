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
    cost_eur: float | None = None  # cost of the whole analysis, including an escalation


def normalize(scores: dict[str, float]) -> dict[str, float]:
    """Scale to a distribution rounded to 3 decimals; the rounding residual goes to the top key."""
    total = sum(scores.values()) or 1.0
    probs = {k: round(v / total, 3) for k, v in scores.items()}
    top = max(probs, key=probs.get)
    probs[top] = round(probs[top] + 1 - sum(probs.values()), 3)
    return probs


def recent(signals, limit: int = MAX_SIGNALS):
    return sorted(signals, key=lambda s: (s.date, s.id or 0), reverse=True)[:limit]


def detect(customer, signals, use_ai: bool = True, timeout_seconds: float | None = None, retries: int = 0) -> Detection:
    """The detection pipeline (settings.detector, default "cascade"):

    1. Jev answers when its calibrated confidence is at least JEV_ESCALATION_THRESHOLD (most customers, ~0.3 s).
    2. Otherwise, or if Jev fails, Gemini decides.
    3. If the AI is unavailable, the deterministic rules answer, so detection never fails.

    timeout_seconds defaults to the interactive limits; seeding passes a longer one plus retries.
    """
    from app.config import settings
    from app.detection import gemini, jev, rules

    latest = recent(signals)
    mode = settings.detector if use_ai else "rules"
    unsure = None

    if mode in ("cascade", "jev") and jev.is_configured():
        answer = jev.detect_safe(customer, latest, timeout_seconds=timeout_seconds, retries=retries)
        if answer is not None and (mode == "jev" or answer.confidence >= settings.jev_escalation_threshold):
            return answer
        unsure = answer

    if mode in ("cascade", "gemini") and gemini.is_configured():
        answer = gemini.detect(customer, latest, timeout_seconds=timeout_seconds, retries=retries)
        if answer is not None:
            answer.cost_eur = gemini.cost_eur(answer)
            if unsure is not None:
                answer.cost_eur += unsure.cost_eur or 0
                answer.rationale = f"Escalated from Jev ({unsure.confidence:.0%} {LABELS[unsure.key].lower()}). {answer.rationale}"
            return answer

    if unsure is not None:  # Jev was unsure but Gemini is unavailable: its calibrated answer beats keyword rules
        return unsure
    return rules.detect(customer, latest)
