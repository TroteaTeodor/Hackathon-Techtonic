from datetime import date
from types import SimpleNamespace

from app.detection import rules
from app.interventions import CATALOG, pinch_delivery, plan
from app.twin import build_twin
from tests.helpers import customer, story_signals

TODAY = date(2026, 9, 30)


def detection(key, confidence, stress=0.1, receptiveness=2):
    probs = {key: confidence}
    return SimpleNamespace(key=key, confidence=confidence, probabilities=probs, stress=stress,
                           receptiveness=receptiveness, rationale="test signals")


def empty_twin():
    return build_twin(3000, story_signals("jan", TODAY))


def by_key(items):
    return {i["key"]: i for i in items}


def test_catalog_covers_every_trigger():
    triggers = {e["trigger"] for e in CATALOG.values()}
    assert {"moving_home", "growing_family", "new_job", "approaching_retirement", "buying_car", "travel_abroad",
            "financial_stress", "pinch", "surplus"} <= triggers
    assert all(e["line"] in ("banking", "insurance", "investing", "support") for e in CATALOG.values())


def test_stressed_customer_gets_support_not_sales():
    signals = story_signals("julie", TODAY)
    c = customer(first_name="Julie", balance=-420)
    det = rules.detect(c, sorted(signals, key=lambda s: s.date, reverse=True)[:40])
    items = plan(c, det, build_twin(c.balance, signals, det.key, det.confidence), TODAY)
    support = [i for i in items if i["line"] == "support"]
    assert support and all(i["status"] == "review" and i["channel"] == "advisor" for i in support)
    assert not [i for i in items if i["line"] != "support" and i["status"] == "delivered"]


def test_confident_moment_is_delivered():
    items = by_key(plan(customer(), detection("moving_home", 0.85), empty_twin(), TODAY))
    assert items["moving_home_bundle"]["status"] == "delivered"
    assert items["moving_home_bundle"]["channel"] == "app"
    assert any("85%" in r for r in items["moving_home_bundle"]["reasons"])


def test_no_consent_holds_sales():
    items = by_key(plan(customer(marketing_consent=False), detection("moving_home", 0.9), empty_twin(), TODAY))
    assert items["moving_home_bundle"]["status"] == "held"


def test_not_receptive_holds_moment_interventions():
    items = by_key(plan(customer(), detection("moving_home", 0.9, receptiveness=0), empty_twin(), TODAY))
    assert items["moving_home_bundle"]["status"] == "held"


def test_minimal_proactivity_holds_moment_but_keeps_pinch_warning():
    signals = story_signals("sara", TODAY)
    twin = build_twin(9800, signals, "moving_home", 0.9)
    items = by_key(plan(customer(proactivity="minimal"), detection("moving_home", 0.9), twin, TODAY))
    assert items["moving_home_bundle"]["status"] == "held"
    assert items["pinch_point_bridge"]["status"] == "delivered"


def test_thresholds_per_proactivity():
    balanced = by_key(plan(customer(proactivity="balanced"), detection("moving_home", 0.68), empty_twin(), TODAY))
    proactive = by_key(plan(customer(proactivity="proactive"), detection("moving_home", 0.68), empty_twin(), TODAY))
    assert balanced["moving_home_bundle"]["status"] == "held"
    assert proactive["moving_home_bundle"]["status"] == "review"


def test_pinch_delivery_is_21_days_before_the_month():
    assert pinch_delivery("2027-03", TODAY) == date(2027, 2, 8)
    assert pinch_delivery("2026-10", TODAY) == TODAY  # already passed -> today


def test_every_intervention_has_reasons():
    signals = story_signals("sara", TODAY)
    twin = build_twin(9800, signals, "moving_home", 0.9)
    for item in plan(customer(), detection("moving_home", 0.9), twin, TODAY):
        assert item["reasons"]


def test_stress_moment_with_low_score_still_gets_support_only():
    """Review finding: key=financial_stress with stress < 0.6 must still trigger the guardrail."""
    signals = story_signals("sara", TODAY)
    twin = build_twin(9800, signals, "moving_home", 0.9)  # has a pinch point
    items = plan(customer(), detection("financial_stress", 0.64, stress=0.45), twin, TODAY)
    keys = {i["key"]: i for i in items}
    assert keys["stress_budget_coach"]["status"] == "review"
    assert "pinch_point_bridge" not in keys  # no bridge-loan offer
    assert not [i for i in items if i["line"] != "support" and i["status"] == "delivered"]
