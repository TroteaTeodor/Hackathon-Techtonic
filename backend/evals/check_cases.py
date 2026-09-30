"""Validate hard-case files:  docker compose exec backend python -m evals.check_cases evals/hard_cases.json

Only .json files inside backend/evals/ can be checked.
"""
import json
import re
import sys
from pathlib import Path

from app.detection.rules import KEYWORDS

EVALS_DIR = Path(__file__).resolve().parent
MOMENTS = ["moving_home", "growing_family", "new_job", "approaching_retirement", "buying_car",
           "travel_abroad", "financial_stress", "no_clear_moment"]
KINDS = {"transaction", "app_event", "search", "contact"}


class CaseError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise CaseError(message)


def safe_path(raw: str) -> Path:
    """Resolve a user-supplied path and refuse anything outside backend/evals/ or that isn't .json."""
    path = Path(raw).resolve()
    if path.suffix != ".json" or not path.is_relative_to(EVALS_DIR) or not path.is_file():
        raise SystemExit(f"refusing {raw!r}: only existing .json files inside {EVALS_DIR} can be checked")
    return path


def hits(text):
    t = text.lower()
    return {m for m, words in KEYWORDS.items() for w in words if w.rstrip("*") in t}


def check_case(c, ids):
    cid = c.get("id", "?")
    require(isinstance(cid, str) and re.fullmatch(r"[a-z0-9_]+", cid), "id must be snake_case")
    require(cid not in ids, "duplicate id")
    ids.add(cid)
    require(c.get("label") in MOMENTS, "bad label")
    require(c.get("type") in ("paraphrase", "trap"), "type must be paraphrase or trap")
    require(isinstance(c.get("note"), str) and 5 <= len(c["note"]) <= 140, "note 5..140 chars")
    require(isinstance(c.get("age"), int) and 18 <= c["age"] <= 90, "age 18..90")
    require(isinstance(c.get("balance"), (int, float)), "balance number")
    sigs = c.get("signals")
    require(isinstance(sigs, list) and 1 <= len(sigs) <= 6, "1..6 signals")
    found = set()
    for s in sigs:
        require(isinstance(s, dict) and set(s) == {"days_ago", "kind", "description", "amount"}, "signal keys")
        require(isinstance(s["days_ago"], int) and 1 <= s["days_ago"] <= 30, "days_ago 1..30")
        require(s["kind"] in KINDS, "bad kind")
        require(isinstance(s["description"], str) and 3 <= len(s["description"]) <= 200, "description 3..200")
        if s["kind"] == "transaction":
            require(isinstance(s["amount"], (int, float)) and s["amount"] != 0, "transaction needs non-zero amount")
        else:
            require(s["amount"] is None, "non-transaction amount must be null")
        found |= hits(s["description"])
    if c["type"] == "paraphrase":
        require(c["label"] != "no_clear_moment", "paraphrase needs a real moment")
        require(not found, f"paraphrase must avoid ALL rule keywords, found: {sorted(found)}")
    else:
        require(found - {c["label"]}, "trap must contain a keyword of a DIFFERENT moment than its label")


def check(raw_path):
    path = safe_path(raw_path)
    data = json.loads(path.read_text())
    if not isinstance(data, list) or not data:
        print(f"{path.name}: top level must be a non-empty list")
        return False
    errors, ids = [], set()
    for c in data:
        try:
            check_case(c, ids)
        except (CaseError, KeyError, TypeError, AttributeError) as e:
            errors.append(f"{c.get('id', '?') if isinstance(c, dict) else '?'}: {e}")
    labels = {}
    for c in data:
        if isinstance(c, dict):
            labels[c.get("label")] = labels.get(c.get("label"), 0) + 1
    print(f"{path.name}: {len(data)} cases, {len(errors)} errors, labels={labels}")
    for e in errors:
        print("  -", e)
    return not errors


if __name__ == "__main__":
    sys.exit(0 if all(check(p) for p in sys.argv[1:]) else 1)
