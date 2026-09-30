"""Jev (OpenRouter Decisions API): typed questions with calibrated probabilities.

The first step of the detection cascade (see detect() in __init__.py and design.md decision 1).
Needs OPENROUTER_API_KEY.
"""

import logging
import time

import httpx

from app.config import settings
from app.detection import Detection, normalize
from app.detection.gemini import build_prompt
from app.schemas import MOMENT_KEYS

logger = logging.getLogger(__name__)

DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"

MOMENT_CRITERIA = {
    "moving_home": "Buying, renting or moving to a new home.",
    "growing_family": "Expecting a baby, recently had or adopted a child.",
    "new_job": "Started a new job, changed employer or received a first salary.",
    "approaching_retirement": "Nearing or entering retirement.",
    "buying_car": "Shopping for or buying a vehicle.",
    "travel_abroad": "Planning or on a trip abroad.",
    "financial_stress": "Missed payments, overdraft, debt collection, mini-loans or a sharp income drop.",
    "no_clear_moment": "Routine activity with no significant life change.",
}
QUESTIONS = {
    "moment": {
        "type": "choice",
        "instructions": "Which life moment is this bank customer in, based on their profile and recent signals?",
        "criteria": MOMENT_CRITERIA,
    },
    "stress": {
        "type": "noul",
        "instructions": "Is this customer showing signs of financial difficulty?",
        "criteria": {
            "true": "Missed or returned payments, overdraft, collection, mini-loans, declined cards or a sharp income drop.",
            "false": "Finances look stable.",
        },
    },
    "receptiveness": {
        "type": "score",
        "instructions": "How open is this customer to hearing from their bank right now?",
        "criteria": ["Not the right time to reach out", "Open to a light, helpful nudge", "Actively looking for help"],
    },
}


def is_configured() -> bool:
    return settings.ai_enabled and bool(settings.openrouter_api_key)


def _evidence(signals, limit: int = 3) -> str:
    """The most recent signals that aren't routine monthly payments, to explain Jev's answer."""
    counts: dict[str, int] = {}
    for s in signals:
        counts[s.description] = counts.get(s.description, 0) + 1
    distinctive = [
        s for s in signals
        if s.kind in ("search", "contact") or (s.kind != "app_event" and counts[s.description] == 1)
    ]
    picked = distinctive[:limit] or signals[:limit]
    return "; ".join(s.description for s in picked)


def detect_safe(customer, signals, *, timeout_seconds: float | None = None, retries: int = 0) -> Detection | None:
    """detect() that returns None instead of raising; retries transient errors (429/5xx) when asked."""
    for attempt in range(retries + 1):
        try:
            return detect(customer, signals, timeout_seconds=timeout_seconds or settings.jev_timeout_seconds)
        except Exception as err:
            transient = isinstance(err, httpx.TimeoutException) or any(c in str(err) for c in ("429", "500", "502", "503", "504"))
            if transient and attempt < retries:
                time.sleep(1 + attempt)
                continue
            logger.warning("Jev detection failed: %s", str(err)[:200])
            return None
    return None


def detect(customer, signals, *, timeout_seconds: float = 30) -> Detection:
    """Raises on HTTP or format errors; callers decide whether to fall back to rules."""
    res = httpx.post(
        DECISIONS_URL,
        headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
        json={"model": settings.jev_model, "state": build_prompt(customer, signals), "questions": QUESTIONS},
        timeout=timeout_seconds,
    )
    res.raise_for_status()
    body = res.json()
    answers = body["answers"]
    probs = {k: float(answers["moment"]["probabilities"].get(k, 0.0)) for k in MOMENT_KEYS}
    probs = normalize(probs)
    key = answers["moment"]["choice"]
    if key not in MOMENT_KEYS:
        raise ValueError(f"unknown moment {key!r}")
    usage = body.get("usage", {})
    detection = Detection(
        key=key,
        confidence=probs[key],
        probabilities=probs,
        stress=round(float(answers["stress"]["noul"]), 2),
        receptiveness=max(0, min(2, round(float(answers["receptiveness"]["score"])))),
        rationale=f"Based on {_evidence(signals)}.",
        source="jev",
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
    )
    detection.cost_usd = usage.get("cost")
    # OpenRouter reports USD; the proof of concept treats it as EUR (≈ parity) for the scale view.
    detection.cost_eur = float(detection.cost_usd) if detection.cost_usd is not None else None
    return detection
