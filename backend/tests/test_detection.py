from types import SimpleNamespace

import pytest

from app.detection import detect, gemini, recent, rules
from tests.helpers import customer, story_signals

EXPECTED = {
    "sara": "moving_home", "lien": "growing_family", "ahmed": "new_job", "marc": "approaching_retirement",
    "julie": "financial_stress", "pieter": "buying_car", "jan": "no_clear_moment",
}


@pytest.mark.parametrize("username,moment", EXPECTED.items())
def test_rules_recognise_every_story(username, moment):
    result = rules.detect(customer(), recent(story_signals(username)))
    assert result.key == moment
    assert result.source == "rules"
    assert abs(sum(result.probabilities.values()) - 1) < 0.01
    if moment != "no_clear_moment":
        assert result.confidence >= 0.6


def test_routine_customer_is_not_over_interpreted():
    result = rules.detect(customer(), recent(story_signals("jan")))
    assert all(p < 0.5 for k, p in result.probabilities.items() if k != "no_clear_moment")


def test_stress_is_high_for_julie_and_low_for_sara():
    assert rules.detect(customer(), recent(story_signals("julie"))).stress >= 0.6
    assert rules.detect(customer(), recent(story_signals("sara"))).stress < 0.2


VALID = """{"probabilities": {"moving_home": 0.87, "growing_family": 0.03, "new_job": 0.01,
  "approaching_retirement": 0.0, "buying_car": 0.02, "travel_abroad": 0.02, "financial_stress": 0.01,
  "no_clear_moment": 0.04}, "stress": 0.08, "receptiveness": 2, "rationale": "Notary deposit."}"""


def test_gemini_valid_response_is_parsed():
    result = gemini.parse(VALID)
    assert result.key == "moving_home" and result.confidence == 0.87 and result.source == "gemini"


@pytest.mark.parametrize("raw", [
    "not json",
    '{"probabilities": {"moving_home": 1.0}, "stress": 0.1, "receptiveness": 1, "rationale": "x"}',
    VALID.replace('"receptiveness": 2', '"receptiveness": 5'),
    VALID.replace("0.87", "3.5"),
])
def test_gemini_malformed_response_is_rejected(raw):
    assert gemini.parse(raw) is None


def test_ai_failure_falls_back_to_rules(monkeypatch):
    class Boom:
        class models:
            @staticmethod
            def generate_content(**_):
                raise TimeoutError("deadline exceeded")

    monkeypatch.setattr(gemini, "is_configured", lambda: True)
    monkeypatch.setattr(gemini, "_client", lambda: Boom)
    result = detect(customer(), story_signals("sara"))
    assert result.source == "rules" and result.key == "moving_home"


def test_malformed_ai_response_falls_back_to_rules(monkeypatch):
    class Bad:
        class models:
            @staticmethod
            def generate_content(**_):
                return SimpleNamespace(text='{"probabilities": {}}', usage_metadata=None)

    monkeypatch.setattr(gemini, "is_configured", lambda: True)
    monkeypatch.setattr(gemini, "_client", lambda: Bad)
    assert detect(customer(), story_signals("sara")).source == "rules"


def test_prompt_contains_only_this_customer():
    prompt = gemini.build_prompt(customer(balance=1234), recent(story_signals("sara")))
    assert "Notaris Peeters" in prompt
    assert "Julie" not in prompt and "Fairway" not in prompt
    assert "password" not in prompt.lower() and "secret" not in prompt.lower()


@pytest.mark.parametrize("text", ["Birthday gift — Fnac", "Suspension repair — Garage Peeters", "Dealership newsletter"])
def test_keywords_match_whole_words_only(text):
    signal = SimpleNamespace(id=1, date=__import__("datetime").date(2026, 9, 1), kind="transaction", description=text, amount=-50)
    assert rules.detect(customer(), [signal]).key == "no_clear_moment"


def test_keyword_stems_still_match():
    from datetime import date
    signals = [SimpleNamespace(id=1, date=date(2026, 9, 1), kind="search", description="Retirement planning calculator", amount=None)]
    assert rules.detect(customer(), signals).key == "approaching_retirement"


def test_transient_error_is_retried_when_asked(monkeypatch):
    calls = []

    class Flaky:
        class models:
            @staticmethod
            def generate_content(**_):
                calls.append(1)
                if len(calls) == 1:
                    raise RuntimeError("504 DEADLINE_EXCEEDED")
                return SimpleNamespace(text=VALID, usage_metadata=None)

    monkeypatch.setattr(gemini, "is_configured", lambda: True)
    monkeypatch.setattr(gemini, "_client", lambda: Flaky)
    assert detect(customer(), story_signals("sara"), retries=1).source == "gemini"
    calls.clear()
    assert detect(customer(), story_signals("sara")).source == "rules"  # live requests don't retry


def test_check_cases_refuses_paths_outside_evals(tmp_path):
    from evals.check_cases import safe_path

    for bad in ["/etc/passwd", "../app/config.py", str(tmp_path / "x.json")]:
        with pytest.raises(SystemExit):
            safe_path(bad)
    assert safe_path("evals/hard_cases.json").name == "hard_cases.json"


# ---- the Jev -> Gemini cascade ----

def _jev_answer(key, confidence):
    from app.detection import Detection
    probs = {k: 0.0 for k in __import__("app.schemas", fromlist=["MOMENT_KEYS"]).MOMENT_KEYS}
    probs[key] = confidence
    probs["no_clear_moment" if key != "no_clear_moment" else "moving_home"] += 1 - confidence
    return Detection(key=key, confidence=confidence, probabilities=probs, stress=0.1, receptiveness=1,
                     rationale="Based on test signals.", source="jev", cost_eur=0.0001)


@pytest.fixture
def cascade(monkeypatch):
    from app.config import settings
    from app.detection import jev

    monkeypatch.setattr(settings, "detector", "cascade")
    monkeypatch.setattr(jev, "is_configured", lambda: True)
    monkeypatch.setattr(gemini, "is_configured", lambda: True)
    calls = {"jev": 0, "gemini": 0}

    def use(jev_answer=None, gemini_answer=None):
        def fake_jev(*_, **__):
            calls["jev"] += 1
            return jev_answer
        def fake_gemini(*_, **__):
            calls["gemini"] += 1
            return gemini_answer
        monkeypatch.setattr(jev, "detect_safe", fake_jev)
        monkeypatch.setattr(gemini, "detect", fake_gemini)
        return calls
    return use


def test_confident_jev_answers_without_gemini(cascade):
    calls = cascade(jev_answer=_jev_answer("moving_home", 0.93))
    result = detect(customer(), story_signals("sara"))
    assert result.source == "jev" and result.key == "moving_home"
    assert calls == {"jev": 1, "gemini": 0}


def test_unsure_jev_escalates_to_gemini(cascade):
    calls = cascade(jev_answer=_jev_answer("travel_abroad", 0.55), gemini_answer=gemini.parse(VALID))
    result = detect(customer(), story_signals("sara"))
    assert result.source == "gemini" and result.key == "moving_home"
    assert "Escalated from Jev" in result.rationale
    assert calls == {"jev": 1, "gemini": 1}
    assert result.cost_eur >= 0.0001


def test_jev_failure_falls_to_gemini(cascade):
    cascade(jev_answer=None, gemini_answer=gemini.parse(VALID))
    assert detect(customer(), story_signals("sara")).source == "gemini"


def test_unsure_jev_is_kept_when_gemini_is_down(cascade):
    cascade(jev_answer=_jev_answer("moving_home", 0.6), gemini_answer=None)
    result = detect(customer(), story_signals("sara"))
    assert result.source == "jev" and result.confidence == 0.6


def test_everything_down_uses_rules(cascade):
    cascade(jev_answer=None, gemini_answer=None)
    assert detect(customer(), story_signals("sara")).source == "rules"


def test_model_confidence_is_capped_at_99():
    from app.detection import normalize

    probs = normalize({"moving_home": 1.0, "new_job": 0.0, "no_clear_moment": 0.0})
    assert probs["moving_home"] == 0.99 and abs(sum(probs.values()) - 1) < 0.001
