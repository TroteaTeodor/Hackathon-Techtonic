"""Gemini-based detection with structured output. Returns None on any problem so callers fall back to rules."""

import json
import logging
import os
import threading

from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.detection import LABELS, Detection
from app.schemas import MOMENT_KEYS

logger = logging.getLogger(__name__)

INSTRUCTIONS = """You are KBC's customer-understanding engine. From one customer's profile and recent
banking signals, estimate which life moment they are in. Moments:
- moving_home: buying, renting or moving to a new home
- growing_family: expecting a baby or recently had a child
- new_job: started a new job, changed employer or received a first salary
- approaching_retirement: nearing or entering retirement
- buying_car: shopping for or buying a vehicle
- travel_abroad: planning or on a trip abroad
- financial_stress: missed payments, overdraft, collection, sharp income drop
- no_clear_moment: routine activity with no significant life change
Give a probability for every moment (they must sum to 1). Be conservative: routine activity is
no_clear_moment. stress is 0..1 (signs of financial difficulty). receptiveness: 0 = not the right time
to reach out, 1 = open to a light nudge, 2 = actively looking for help. rationale: one sentence citing
the signals."""


class _Probabilities(BaseModel):
    moving_home: float
    growing_family: float
    new_job: float
    approaching_retirement: float
    buying_car: float
    travel_abroad: float
    financial_stress: float
    no_clear_moment: float


class _GeminiMoment(BaseModel):
    probabilities: _Probabilities
    stress: float = Field(ge=0, le=1)
    receptiveness: int = Field(ge=0, le=2)
    rationale: str = Field(min_length=1, max_length=400)


def is_configured() -> bool:
    if not settings.ai_enabled:
        return False
    if settings.google_genai_use_vertexai:
        creds = settings.google_application_credentials
        return bool(settings.google_cloud_project) and (not creds or os.path.exists(creds))
    return bool(settings.gemini_api_key)


_client_lock = threading.Lock()
_client_instance = None


def _client():
    # One shared client: creating several concurrently makes the SDK close the shared HTTP connection.
    global _client_instance
    with _client_lock:
        if _client_instance is None:
            from google import genai
            from google.genai import types

            http_options = types.HttpOptions(timeout=int(settings.gemini_timeout_seconds * 1000))
            if settings.google_genai_use_vertexai:
                _client_instance = genai.Client(
                    vertexai=True,
                    project=settings.google_cloud_project,
                    location=settings.google_cloud_location,
                    http_options=http_options,
                )
            else:
                _client_instance = genai.Client(api_key=settings.gemini_api_key, http_options=http_options)
        return _client_instance


def build_prompt(customer, signals) -> str:
    """Only this customer's own profile and signals go into the prompt."""
    payload = {
        "customer": {
            "age": customer.age,
            "city": customer.city,
            "balance_eur": customer.balance,
        },
        "signals": [
            {"date": s.date.isoformat(), "kind": s.kind, "description": s.description, "amount_eur": s.amount}
            for s in signals
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def parse(raw: str) -> Detection | None:
    try:
        result = _GeminiMoment.model_validate_json(raw)
    except ValidationError as err:
        logger.warning("Gemini returned an invalid moment: %s", err.errors()[:2])
        return None
    probs = result.probabilities.model_dump()
    total = sum(probs.values())
    if not 0.9 <= total <= 1.1 or any(p < 0 for p in probs.values()):
        logger.warning("Gemini probabilities don't form a distribution (sum=%.2f)", total)
        return None
    probs = {k: round(v / total, 3) for k, v in probs.items()}
    key = max(probs, key=probs.get)
    probs[key] = round(probs[key] + 1 - sum(probs.values()), 3)
    assert set(probs) == set(MOMENT_KEYS)
    return Detection(
        key=key,
        confidence=probs[key],
        probabilities=probs,
        stress=round(result.stress, 2),
        receptiveness=result.receptiveness,
        rationale=result.rationale,
        source="gemini",
    )


def detect(customer, signals) -> Detection | None:
    from google.genai import types

    try:
        response = _client().models.generate_content(
            model=settings.gemini_model,
            contents=build_prompt(customer, signals),
            config=types.GenerateContentConfig(
                system_instruction=INSTRUCTIONS,
                response_mime_type="application/json",
                response_schema=_GeminiMoment,
                temperature=0,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )
    except Exception as err:  # network, auth, quota, timeout: fall back to rules
        logger.warning("Gemini detection failed, using rules: %s", str(err)[:200])
        return None

    detection = parse(response.text or "")
    if detection is None:
        return None
    usage = response.usage_metadata
    if usage:
        detection.input_tokens = usage.prompt_token_count or 0
        detection.output_tokens = (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)
    logger.info("Gemini: %s (%.2f) for customer %s", detection.key, detection.confidence, customer.id)
    return detection


__all__ = ["LABELS", "detect", "is_configured", "parse", "build_prompt"]
