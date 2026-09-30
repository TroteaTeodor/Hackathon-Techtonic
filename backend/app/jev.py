import logging

import httpx

from app.categories import CATEGORIES
from app.config import settings

logger = logging.getLogger(__name__)

DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"


def categorize(text: str) -> tuple[str, float] | None:
    """Ask Jev which category fits `text`. Returns (category, confidence), or None if unavailable."""
    if not settings.openrouter_api_key:
        return None

    try:
        res = httpx.post(
            DECISIONS_URL,
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json={
                "model": settings.jev_model,
                "state": text,
                "questions": {
                    "category": {
                        "type": "choice",
                        "instructions": "Which category best describes this item?",
                        "criteria": CATEGORIES,
                    }
                },
            },
            timeout=10,
        )
        res.raise_for_status()
        answer = res.json()["answers"]["category"]
        return answer["choice"], answer["confidence"]
    except (httpx.HTTPError, KeyError, ValueError) as err:
        logger.warning("Jev categorization failed: %s", err)
        return None
