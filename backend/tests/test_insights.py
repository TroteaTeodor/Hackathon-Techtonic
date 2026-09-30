from datetime import date
from types import SimpleNamespace

import pytest

from app import insights
from app.detection import rules
from app.interventions import noticed, plan
from app.twin import analyse_history, build_twin, home_purchase
from tests.helpers import customer, story_signals

TODAY = date(2026, 9, 30)


@pytest.mark.parametrize("description,amount,category", [
    ("Salary — Barco NV", 3100, "income"),
    ("Rent — Immo Vandenberghe", -950, "housing"),
    ("Notary deposit — Notaris Peeters", -15000, "housing"),
    ("Netflix — Standard", -15.99, "subscriptions"),
    ("Basic-Fit — membership", -29.99, "subscriptions"),
    ("Groceries — Colruyt", -130, "groceries"),
    ("Energy — Engie", -140, "energy"),
    ("Telecom — Proximus", -55, "telecom"),
    ("Deliveroo — dinner", -32, "dining"),
    ("Kinepolis — tickets", -24, "entertainment"),
    ("Home contents insurance — KBC", -180, "insurance"),
    ("Overdraft interest — KBC", -38.4, "fees"),
    ("Klarna — instalment 2 of 3", -46, "loans"),
    ("Dreambaby — stroller", -429, "family"),
    ("Current account transfer", -50, "other"),  # "rent" must not match inside "current"
])
def test_classify(description, amount, category):
    assert insights.classify(description, amount) == category


def test_subscriptions_with_price_rise():
    subs = {s.name: s for s in insights.subscriptions(story_signals("sara", TODAY))}
    assert set(subs) == {"Netflix", "Spotify", "Basic-Fit"}
    assert subs["Netflix"].monthly_amount == 15.99
    assert subs["Netflix"].price_change.before == 13.99 and subs["Netflix"].price_change.after == 15.99
    assert subs["Spotify"].price_change is None


def test_spending_shares_add_up():
    rows = insights.spending(story_signals("sara", TODAY))
    assert abs(sum(r.share for r in rows) - 1) < 0.01
    housing = next(r for r in rows if r.category == "housing")
    assert housing.monthly_average < 1500  # the €15,000 notary deposit is a one-off, not monthly spend
    assert {"housing", "groceries", "subscriptions"} <= {r.category for r in rows}
    assert "income" not in {r.category for r in rows}


def test_signal_views_flag_recurring():
    views = {v.description: v for v in insights.signal_views(story_signals("sara", TODAY))}
    assert views["Rent — Immo Vandenberghe"].recurring and views["Rent — Immo Vandenberghe"].category == "housing"
    assert not views["Notary deposit — Notaris Peeters"].recurring


def test_moment_amounts_follow_income():
    low = [SimpleNamespace(id=m, date=date(2026, m, 1), kind="transaction", description="Salary — A", amount=2000) for m in range(1, 10)]
    high = [SimpleNamespace(id=m, date=date(2026, m, 1), kind="transaction", description="Salary — A", amount=4500) for m in range(1, 10)]
    a, b = home_purchase(analyse_history(low)[1], low), home_purchase(analyse_history(high)[1], high)
    assert a["payment"] < b["payment"] and a["price"] < b["price"] and a["fees"] < b["fees"]


def test_moment_card_names_the_evidence_and_asks():
    signals = story_signals("sara", TODAY)
    det = SimpleNamespace(key="moving_home", confidence=0.95, probabilities={}, stress=0.05, receptiveness=2, rationale="x")
    items = {i["key"]: i for i in plan(customer(first_name="Sara"), det, build_twin(8000, signals, "moving_home", 0.95),
                                       TODAY, signals=signals)}
    card = items["moving_home_bundle"]
    assert "Notaris Peeters" in card["message"] and "Are you moving?" in card["message"]
    assert card["cta"] == "See my mortgage options"
    assert items["moving_home_insurance"]["cta"] == "Get home insurance"


def test_evidence_prefers_a_transaction():
    signals = sorted(story_signals("sara", TODAY), key=lambda s: s.date, reverse=True)[:40]
    assert rules.evidence("moving_home", signals).kind == "transaction"
    assert "€15,000 payment to Notaris Peeters" in noticed(rules.evidence("moving_home", signals))


def test_stress_cards_never_mention_signals():
    signals = story_signals("julie", TODAY)
    c = customer(first_name="Julie", balance=-420)
    det = rules.detect(c, sorted(signals, key=lambda s: s.date, reverse=True)[:40])
    subs = insights.subscriptions(signals)
    items = plan(c, det, build_twin(c.balance, signals, det.key, det.confidence), TODAY, subs=subs, income=1900, signals=signals)
    assert not [i for i in items if "noticed" in i["message"].lower()]
    review = next(i for i in items if i["key"] == "subscription_review")
    assert review["status"] == "review" and "Netflix went up" in review["message"]


# ---- personalisation (Gemini copy is validated, never trusted) ----

from app import personalize  # noqa: E402


def _ctx(**overrides):
    from app.schemas import CategorySpend
    spending = [CategorySpend(category="dining", label="Eating out", monthly_average=240, share=0.15, recurring_share=0),
                CategorySpend(category="housing", label="Housing", monthly_average=950, share=0.6, recurring_share=1)]
    base = {"first_name": "Sara", "age": 31, "moment": "moving_home", "moment_confidence": 0.95,
            "spending": spending, "subscriptions": [], "monthly_surplus": 700.0, "pinch": None}
    return {**base, **overrides}


def test_suggestions_follow_the_data():
    assert set(personalize.eligible_suggestions(_ctx())) == {"suggest_eating_out_budget", "suggest_auto_savings"}
    assert personalize.eligible_suggestions(_ctx(monthly_surplus=100, spending=[])) == []


CARDS = [{"key": "moving_home_bundle", "title": "Moving home?", "message": "We noticed a €15,000 payment. Are you moving?", "cta": "x"}]


def _raw(message, key="moving_home_bundle", suggestions=()):
    import json
    return json.dumps({"cards": [{"key": key, "title": "Moving home, Sara?", "message": message}],
                       "suggestions": [{"key": k, "message": m} for k, m in suggestions]})


def test_copy_is_accepted_when_it_only_uses_given_facts():
    ctx = _ctx()
    payload = personalize._payload(ctx, CARDS, ["suggest_eating_out_budget"])
    raw = _raw("That €15,000 payment caught our eye. Are you moving?", suggestions=[("suggest_eating_out_budget", "You spend 240 a month eating out.")])
    assert personalize.validate(raw, payload, {"moving_home_bundle"}, {"suggest_eating_out_budget"}, {"moving_home_bundle"}) is not None


@pytest.mark.parametrize("raw", [
    _raw("A €99,999 payment. Are you moving?"),                        # invented number
    _raw("We noticed a €15,000 payment. Congrats on the move!"),      # dropped the confirming question
    _raw("Are you moving?", key="unknown_card"),                        # unknown card
    _raw("Are you moving?", suggestions=[("suggest_energy_loan", "x")]),  # suggestion not eligible
    "not json",
])
def test_bad_copy_is_rejected(raw):
    payload = personalize._payload(_ctx(), CARDS, ["suggest_eating_out_budget"])
    assert personalize.validate(raw, payload, {"moving_home_bundle"}, {"suggest_eating_out_budget"}, {"moving_home_bundle"}) is None


def test_stressed_customers_get_no_generated_copy(client, db, monkeypatch):
    from app import analysis
    from tests.conftest import customer_id

    calls = []
    monkeypatch.setattr(personalize, "write", lambda *a, **k: calls.append(1) or (None, 0, 0))
    assert analysis.personalize_customer(customer_id(db, "Julie")) is False
    assert calls == []


def test_personalized_copy_is_applied_and_kept(client, db, monkeypatch):
    from app import analysis
    from app.models import InterventionRecord
    from tests.conftest import customer_id, login
    from sqlalchemy import select

    sara = customer_id(db, "Sara")

    def fake_write(ctx, cards, eligible):
        assert "moving_home_bundle" in {c["key"] for c in cards}
        return personalize._Copy(cards=[personalize._Card(key="moving_home_bundle", title="Just for you, Sara", message="Are you moving? Here is what we have.")],
                                 suggestions=[]), 10, 5
    monkeypatch.setattr(personalize, "write", fake_write)
    assert analysis.personalize_customer(sara) is True
    db.expire_all()
    row = db.scalar(select(InterventionRecord).where(InterventionRecord.customer_id == sara, InterventionRecord.title == "Just for you, Sara"))
    assert row is not None and row.personalized and "Gemini" in row.reasons[-1]
    login(client, "sara")
    client.put("/me/preferences", json={"proactivity": "balanced"})  # re-plan keeps the personal wording
    titles = [i["title"] for i in client.get("/me/overview").json()["interventions"]]
    assert "Just for you, Sara" in titles
