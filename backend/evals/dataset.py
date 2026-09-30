"""Labelled evaluation cases for life-moment detection.

Three groups:
- story: the 7 scripted demo customers
- population: the 200 generated customers (label = the moment the generator scripted)
- hard: cases that keyword rules get wrong (keyword traps, and moments described without any of the
  rule keywords): 13 written inline below plus evals/hard_cases.json (written by parallel agents and
  checked by evals/check_cases.py). They measure whether the model understands, not just matches.
"""

import json
import random
from dataclasses import dataclass
from pathlib import Path
from datetime import date
from types import SimpleNamespace

from app.seed import POPULATION_SEED, POPULATION_SIZE, STORIES, Story, _base, _history, _population_story

STORY_LABELS = {
    "sara": "moving_home", "lien": "growing_family", "ahmed": "new_job", "marc": "approaching_retirement",
    "julie": "financial_stress", "pieter": "buying_car", "jan": "no_clear_moment",
}


@dataclass
class Case:
    id: str
    group: str
    label: str
    customer: SimpleNamespace
    signals: list
    note: str = ""


def _routine(salary=3000, rent=900):
    return _base("Salary — employer", salary, "Rent — landlord", rent, "Energy — Engie", 140,
                 "Telecom — Proximus", 55, "Groceries — Colruyt", 520, 500)


def _hard(n, label, note, recent, age=35, balance=4000.0, history_only=(), salary=3000):
    return Story(f"hard{n}", "Test", f"Case{n}", age, "Gent", balance, True, "balanced",
                 _routine(salary), recent=list(recent), history_only=list(history_only), label=label), note


HARD = [
    # Keyword traps: the rules match a keyword, but the situation is something else.
    _hard(1, "no_clear_moment", "notary for an inheritance, not a home purchase",
          [(6, "transaction", "Notary fees — estate settlement of late father, Notaris Claes", -2400),
           (9, "contact", "Asked about inheritance tax on a savings account", None)]),
    _hard(2, "no_clear_moment", "yearly pension savings at 30 is routine, not retirement",
          [(10, "transaction", "Pension savings — yearly contribution", -990)], age=30),
    _hard(3, "no_clear_moment", "gift for someone else's baby",
          [(4, "transaction", "Dreambaby — gift for a friend's baby shower", -45)]),
    _hard(4, "no_clear_moment", "car dealer for maintenance, not a purchase",
          [(7, "transaction", "Dealer — annual car service, Volvo Brugge", -380)]),
    _hard(5, "no_clear_moment", "airline refund for a cancelled trip",
          [(5, "transaction", "Brussels Airlines — refund cancelled flight", 210)]),
    # Paraphrases: the moment is clear, but none of the rule keywords appear.
    _hard(6, "moving_home", "moving described through movers, rental guarantee and new utilities",
          [(3, "transaction", "Van Damme Transport — movers", -1450),
           (8, "transaction", "Rental guarantee deposit — blocked account", -2700),
           (5, "transaction", "Fluvius — new electricity connection, Kortrijk", -95),
           (2, "app_event", "Changed home address in the app", None)]),
    _hard(7, "growing_family", "newborn described through diapers and child allowance",
          [(4, "transaction", "Pampers — newborn diapers", -39),
           (6, "transaction", "Groeipakket — starting allowance", 1200),
           (9, "contact", "Asked to add a child as co-holder on a savings account", None)]),
    _hard(8, "new_job", "salary from a new employer, no job keywords",
          [(6, "transaction", "Salary — Deloitte Belgium", 3400)],
          history_only=[("Salary — Accenture Belgium", 3000, 1, 11, 2)], salary=0),
    _hard(9, "financial_stress", "stress through buy-now-pay-later, mini loans and declined cards",
          [(2, "app_event", "Card payment declined — insufficient funds", None),
           (5, "transaction", "Klarna — instalment 2 of 3", -46),
           (7, "transaction", "Cofidis — mini loan payout", 500),
           (12, "transaction", "Klarna — instalment 1 of 3", -46)], balance=-310),
    _hard(10, "approaching_retirement", "end of career through a group-insurance payout",
          [(4, "transaction", "Group insurance payout — AG Insurance", 48000),
           (9, "contact", "Asked how to spread a large lump sum over the coming years", None)], age=64),
    _hard(11, "travel_abroad", "trip described through foreign card payments",
          [(3, "transaction", "KLM — tickets Brussels to Lisbon", -380),
           (2, "transaction", "Card payment in Lisboa, Portugal", -64),
           (1, "transaction", "Card payment in Lisboa, Portugal", -38)]),
    _hard(12, "buying_car", "car purchase through second-hand listing and registration",
          [(6, "search", "2dehands — used Toyota Yaris hybrid", None),
           (3, "transaction", "DIV — number plate registration", -30),
           (2, "transaction", "Autosecurite — technical inspection", -45)]),
    _hard(13, "no_clear_moment", "control: routine month with a big grocery run",
          [(3, "transaction", "Groceries — Colruyt (party)", -210)]),
]


HARD_CASES_FILE = Path(__file__).parent / "hard_cases.json"


def _load_hard_file():
    """Extra hard cases (keyword-free paraphrases and keyword traps), validated by evals/check_cases.py."""
    if not HARD_CASES_FILE.exists():
        return []
    out = []
    for c in json.loads(HARD_CASES_FILE.read_text()):
        story = Story(c["id"], "Test", c["id"], c["age"], "Gent", float(c["balance"]), True, "balanced", _routine(),
                      recent=[(s["days_ago"], s["kind"], s["description"], s["amount"]) for s in c["signals"]],
                      label=c["label"])
        out.append((story, f"{c['type']}: {c['note']}"))
    return out


def _signals(story: Story, today: date):
    rows = _history(story, today, random.Random(story.username))
    return [SimpleNamespace(id=i, date=d, kind=k, description=desc, amount=a) for i, (d, k, desc, a) in enumerate(rows)]


def _customer(story: Story, i: int):
    return SimpleNamespace(id=i, first_name=story.first_name, last_name=story.last_name, age=story.age, city=story.city,
                           balance=story.balance, marketing_consent=story.consent, proactivity=story.proactivity)


def build(today: date | None = None, groups=("story", "population", "hard")) -> list[Case]:
    today = today or date.today()
    cases: list[Case] = []
    if "story" in groups:
        for i, s in enumerate(STORIES):
            cases.append(Case(f"story:{s.username}", "story", STORY_LABELS[s.username], _customer(s, i), _signals(s, today)))
    if "population" in groups:
        rng = random.Random(POPULATION_SEED)
        for n in range(POPULATION_SIZE):
            s = _population_story(rng, n)
            # _insert() draws history amounts from the same rng; mirror that so the data matches the seed.
            rows = _history(s, today, rng)
            signals = [SimpleNamespace(id=j, date=d, kind=k, description=desc, amount=a) for j, (d, k, desc, a) in enumerate(rows)]
            cases.append(Case(f"population:{n}", "population", s.label, _customer(s, 100 + n), signals))
    if "hard" in groups:
        for n, (s, note) in enumerate(HARD + _load_hard_file()):
            cases.append(Case(f"hard:{s.username}", "hard", s.label, _customer(s, 1000 + n), _signals(s, today), note))
    return cases
