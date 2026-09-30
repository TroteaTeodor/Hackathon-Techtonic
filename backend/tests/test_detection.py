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
