"""Validate hard-case files:  docker compose exec backend python -m evals.check_cases evals/hard_cases.json"""
import json
import re
import sys

from app.detection.rules import KEYWORDS

MOMENTS = ["moving_home", "growing_family", "new_job", "approaching_retirement", "buying_car",
           "travel_abroad", "financial_stress", "no_clear_moment"]
KINDS = {"transaction", "app_event", "search", "contact"}


def hits(text):
    t = text.lower()
    return {m for m, words in KEYWORDS.items() for w in words if w in t}


def check(path):
    data = json.load(open(path))
    assert isinstance(data, list) and data, "top level must be a non-empty list"
    errors, ids = [], set()
    for c in data:
        cid = c.get("id", "?")
        try:
            assert re.fullmatch(r"[a-z0-9_]+", cid), "id must be snake_case"
            assert cid not in ids, "duplicate id"; ids.add(cid)
            assert c["label"] in MOMENTS, "bad label"
            assert c["type"] in ("paraphrase", "trap"), "type must be paraphrase or trap"
            assert isinstance(c["note"], str) and 5 <= len(c["note"]) <= 140, "note 5..140 chars"
            assert isinstance(c["age"], int) and 18 <= c["age"] <= 90, "age 18..90"
            assert isinstance(c["balance"], (int, float)), "balance number"
            sigs = c["signals"]; assert 1 <= len(sigs) <= 6, "1..6 signals"
            found = set()
            for s in sigs:
                assert set(s) == {"days_ago", "kind", "description", "amount"}, f"signal keys {sorted(s)}"
                assert isinstance(s["days_ago"], int) and 1 <= s["days_ago"] <= 30, "days_ago 1..30"
                assert s["kind"] in KINDS, "bad kind"
                assert 3 <= len(s["description"]) <= 200, "description 3..200"
                if s["kind"] == "transaction":
                    assert isinstance(s["amount"], (int, float)) and s["amount"] != 0, "transaction needs non-zero amount"
                else:
                    assert s["amount"] is None, "non-transaction amount must be null"
                found |= hits(s["description"])
            if c["type"] == "paraphrase":
                assert c["label"] != "no_clear_moment", "paraphrase needs a real moment"
                assert not found, f"paraphrase must avoid ALL rule keywords, found: {sorted(found)}"
            else:
                assert found - {c["label"]}, "trap must contain a keyword of a DIFFERENT moment than its label"
        except (AssertionError, KeyError, TypeError) as e:
            errors.append(f"{cid}: {e}")
    labels = {}
    for c in data:
        labels[c.get("label")] = labels.get(c.get("label"), 0) + 1
    print(f"{path}: {len(data)} cases, {len(errors)} errors, labels={labels}")
    for e in errors:
        print("  -", e)
    return not errors


if __name__ == "__main__":
    sys.exit(0 if all(check(p) for p in sys.argv[1:]) else 1)
