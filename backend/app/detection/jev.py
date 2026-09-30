"""Jev (OpenRouter Decisions API) detector: typed questions with calibrated probabilities.

Used as an A/B variant in the evals (`--variants jev`). Needs OPENROUTER_API_KEY.
"""

import httpx

from app.config import settings
from app.detection import Detection, normalize
from app.detection.gemini import build_prompt
from app.schemas import MOMENT_KEYS

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
    return bool(settings.openrouter_api_key)


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
        rationale=f"Jev: {key} ({probs[key]:.0%})",
        source="jev",
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
    )
    detection.cost_usd = usage.get("cost")
    return detection
