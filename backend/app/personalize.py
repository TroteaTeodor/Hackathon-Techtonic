"""Personal suggestions and card copy, written by Gemini Flash from the customer's categorised data.

Split of responsibilities (design.md decision 3):
- The policy (interventions.py) decides WHETHER and WHAT: guardrails, consent, stress, proactivity. Deterministic.
- This module decides HOW it's said, and which of the already-eligible spending offers fit best (at most 2).

Every AI output is validated: known keys only, no numbers that aren't in the customer's data, length limits, and
moment cards keep their confirming question. Anything invalid falls back to the template text. Customers under
financial stress never get generated copy.
"""

import json
import logging
import re

from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.twin import euro

logger = logging.getLogger(__name__)

MAX_SUGGESTIONS = 2
TITLE_MAX = 70
MESSAGE_MAX = 320


# Spending-based offers: eligible only when the categorised data supports them. The policy then gates them.
def _spend(ctx, *cats) -> float:
    return sum(r.monthly_average for r in ctx["spending"] if r.category in cats)


def _share(ctx, *cats) -> float:
    return sum(r.share for r in ctx["spending"] if r.category in cats)


SUGGESTIONS: dict[str, dict] = {
    "suggest_eating_out_budget": dict(
        line="support", channel="app", title="A budget for eating out", cta="Set a budget in KBC Mobile",
        eligible=lambda c: _share(c, "dining", "entertainment") >= 0.12,
        facts=lambda c: [f"Eating out and entertainment: {euro(_spend(c, 'dining', 'entertainment'))} a month "
                         f"({_share(c, 'dining', 'entertainment'):.0%} of spending)"],
        template="You spend about {amount} a month on eating out and going out. Set a monthly budget in KBC Mobile "
                 "and get a nudge before you go over.",
        amount=lambda c: euro(_spend(c, "dining", "entertainment")),
    ),
    "suggest_auto_savings": dict(
        line="banking", channel="app", title="Save automatically every month", cta="Start an automatic savings plan",
        eligible=lambda c: _spend(c, "savings") == 0 and c["monthly_surplus"] >= 300,
        facts=lambda c: [f"Money left over after regular costs: about {euro(c['monthly_surplus'])} a month",
                         "No savings transfers in the last 3 months"],
        template="About {amount} is left over each month after your regular costs. Move part of it to savings "
                 "automatically, the day your salary arrives.",
        amount=lambda c: euro(c["monthly_surplus"]),
    ),
    "suggest_energy_loan": dict(
        line="banking", channel="app", title="Lower your energy bill", cta="See the energy-saving loan",
        eligible=lambda c: _spend(c, "energy") >= 150,
        facts=lambda c: [f"Energy and water: {euro(_spend(c, 'energy'))} a month"],
        template="Energy and water cost you about {amount} a month. An energy-saving loan for insulation "
                 "or solar panels can pay for itself.",
        amount=lambda c: euro(_spend(c, "energy")),
    ),
    "suggest_travel_insurance": dict(
        line="insurance", channel="app", title="Travel cover for the whole year", cta="Add yearly travel insurance",
        eligible=lambda c: _spend(c, "travel") > 0 and c["moment"] != "travel_abroad",
        facts=lambda c: [f"Travel spending in the last 3 months: about {euro(_spend(c, 'travel') * 3)}"],
        template="You've booked travel recently. A yearly travel insurance covers every trip, for less than "
                 "insuring each one.",
        amount=lambda c: "",
    ),
}


def eligible_suggestions(ctx) -> list[str]:
    return [k for k, s in SUGGESTIONS.items() if s["eligible"](ctx)]


def suggestion_item(key: str, ctx) -> dict:
    s = SUGGESTIONS[key]
    return {"key": key, "title": s["title"], "message": s["template"].format(amount=s["amount"](ctx)),
            "line": s["line"], "channel": s["channel"], "cta": s["cta"],
            "reasons": ["Picked from your spending: " + "; ".join(s["facts"](ctx))]}


# ---------- Gemini copywriter ----------

INSTRUCTIONS = """You write short, warm messages for KBC bank customers in their banking app. English, second person.
You get the customer's categorised data, the cards our policy already decided to show (with template text), and a
list of eligible extra suggestions. Rewrite each card so it feels personal, using at most two concrete facts from the
data. Pick at most two suggestions from the eligible list that fit this customer best and explain why in one or two
sentences ("This seems interesting for you because ...").
Hard rules: never invent numbers, prices, products or promises; only use numbers that appear in the input. Keep the
product and the call to action of each card. If a card's template asks a confirming question (like "Are you moving?"),
keep a question, and keep the "We noticed ..." sentence that names the signal. The call to action is a separate button:
don't repeat it in the message. Write amounts like €1,417 or €15.99 (never "600.0" or "194.0 euros"). Don't mention
the customer's age, and never refer to debt, missed payments or anything sensitive. No pressure, no guaranteed approval.
Titles at most 70 characters, messages at most 320."""


class _Card(BaseModel):
    key: str
    title: str = Field(max_length=TITLE_MAX)
    message: str = Field(max_length=MESSAGE_MAX)


class _Suggestion(BaseModel):
    key: str
    message: str = Field(max_length=MESSAGE_MAX)


class _Copy(BaseModel):
    cards: list[_Card]
    suggestions: list[_Suggestion] = Field(max_length=MAX_SUGGESTIONS)


_NUMBER = re.compile(r"\d[\d.,]*\d|\d")
SMALL_NUMBERS = 31  # counts, days and dates ("3 subscriptions", "21 days", "18 September") are fine


def _numbers(text: str) -> set[float]:
    out = set()
    for raw in _NUMBER.findall(text):
        try:
            out.add(float(raw.replace(",", "").rstrip(".")))
        except ValueError:
            continue
    return out


def _known(number: float, allowed: set[float]) -> bool:
    """A number is known if it's small, or matches a value from the data up to rounding (187.2 → 187, 695.64 → 696)."""
    if number <= SMALL_NUMBERS and number == int(number):
        return True
    return any(abs(number - a) <= max(0.51, 0.005 * abs(a)) for a in allowed)


def _only_known(text: str, allowed: set[float]) -> bool:
    return all(_known(n, allowed) for n in _numbers(text))


def build_context(customer, detection, spending, subs, twin, monthly_surplus: float) -> dict:
    return {
        "first_name": customer.first_name, "age": customer.age, "moment": detection.key,
        "moment_confidence": round(detection.confidence, 2), "spending": spending, "subscriptions": subs,
        "monthly_surplus": round(monthly_surplus, 2),
        "pinch": twin.pinch_points[0].model_dump() if twin.pinch_points else None,
    }


def _payload(ctx, cards, eligible) -> dict:
    return {
        "customer": {"first_name": ctx["first_name"], "age": ctx["age"]},
        "detected_moment": ctx["moment"], "confidence": ctx["moment_confidence"],
        "spending_per_month": [{"category": r.label, "eur": r.monthly_average, "share": r.share} for r in ctx["spending"][:6]],
        "subscriptions": [{"name": s.name, "eur_per_month": s.monthly_amount,
                           "price_change": s.price_change.model_dump() if s.price_change else None} for s in ctx["subscriptions"]],
        "pinch_point": ctx["pinch"],
        "cards": [{"key": c["key"], "title": c["title"], "template": c["message"], "cta": c.get("cta")} for c in cards],
        "eligible_suggestions": [{"key": k, "title": SUGGESTIONS[k]["title"], "cta": SUGGESTIONS[k]["cta"],
                                  "facts": SUGGESTIONS[k]["facts"](ctx)} for k in eligible],
    }


def validate(raw: str, payload: dict, card_keys: set[str], eligible: set[str], questions: set[str]) -> _Copy | None:
    try:
        copy = _Copy.model_validate_json(raw)
    except ValidationError as err:
        logger.warning("Copy rejected (schema): %s", err.errors()[:1])
        return None
    allowed = {abs(n) for n in _numbers(json.dumps(payload, ensure_ascii=False))}
    for card in copy.cards:
        if card.key not in card_keys or not _only_known(card.title + " " + card.message, allowed):
            logger.warning("Copy rejected (unknown key or invented number) for %s", card.key)
            return None
        if card.key in questions and "?" not in card.message:
            logger.warning("Copy rejected (dropped the confirming question) for %s", card.key)
            return None
    for s in copy.suggestions:
        if s.key not in eligible or not _only_known(s.message, allowed):
            logger.warning("Copy rejected (suggestion %s not eligible or invented number)", s.key)
            return None
    return copy


def enabled() -> bool:
    from app.detection import gemini

    return settings.personalize_with_ai and gemini.is_configured()


def write(ctx, cards: list[dict], eligible: list[str]) -> tuple[_Copy | None, int, int]:
    """One Gemini Flash call for all of a customer's cards. Returns (copy or None, input tokens, output tokens)."""
    from app.detection import gemini

    if not settings.personalize_with_ai or not gemini.is_configured() or not (cards or eligible):
        return None, 0, 0
    from google.genai import types

    payload = _payload(ctx, cards, eligible)
    try:
        response = gemini._client().models.generate_content(
            model=settings.gemini_model,
            contents=json.dumps(payload, ensure_ascii=False),
            config=types.GenerateContentConfig(
                system_instruction=INSTRUCTIONS, response_mime_type="application/json", response_schema=_Copy,
                temperature=0.4, thinking_config=types.ThinkingConfig(thinking_level=settings.copy_thinking_level.upper()),
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                http_options=types.HttpOptions(timeout=int(settings.copy_timeout_seconds * 1000)),
            ),
        )
    except Exception as err:
        logger.warning("Copy generation failed, using templates: %s", str(err)[:160])
        return None, 0, 0
    usage = response.usage_metadata
    tin = (usage.prompt_token_count or 0) if usage else 0
    tout = ((usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)) if usage else 0
    questions = {c["key"] for c in cards if "?" in c["message"]}
    return validate(response.text or "", payload, {c["key"] for c in cards}, set(eligible), questions), tin, tout
