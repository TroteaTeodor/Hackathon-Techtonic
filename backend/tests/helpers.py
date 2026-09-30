import random
from datetime import date
from types import SimpleNamespace

from app.seed import STORIES, _history


def story(username: str):
    return next(s for s in STORIES if s.username == username)


def story_signals(username: str, today: date | None = None):
    s = story(username)
    rows = _history(s, today or date.today(), random.Random(s.username))
    return [SimpleNamespace(id=i, date=d, kind=k, description=desc, amount=a) for i, (d, k, desc, a) in enumerate(rows)]


def customer(**overrides):
    base = dict(id=1, first_name="Test", last_name="Customer", age=35, city="Gent",
                marketing_consent=True, proactivity="balanced", balance=5000.0)
    return SimpleNamespace(**{**base, **overrides})
