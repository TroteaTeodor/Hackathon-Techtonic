from sqlalchemy import func, select

from app.models import Customer, User
from app.seed import POPULATION_SIZE, STORIES, seed


def test_seed_is_idempotent(client, db):
    seed(db, use_ai=False)
    seed(db, use_ai=False)
    assert db.scalar(select(func.count()).select_from(Customer).where(Customer.is_story)) == len(STORIES) == 7
    assert db.scalar(select(func.count()).select_from(Customer).where(~Customer.is_story)) == POPULATION_SIZE
    assert db.scalar(select(func.count()).select_from(User)) == len(STORIES) + 1


def test_population_is_deterministic():
    import random

    from app.seed import _population_story

    def names():
        rng = random.Random(42)
        return [(s.first_name, s.last_name, s.city, len(s.recent)) for s in (_population_story(rng, n) for n in range(POPULATION_SIZE))]

    assert names() == names()


def test_demo_passwords_are_hashed(client, db):
    for user in db.scalars(select(User)):
        assert user.password_hash.startswith("scrypt$")
        assert "test-demo-password" not in user.password_hash


def test_story_customers_have_income_and_costs(client, db):
    from app.analysis import customer_signals

    for c in db.scalars(select(Customer).where(Customer.is_story)):
        signals = customer_signals(db, c.id)
        assert any((s.amount or 0) > 0 for s in signals), c.first_name
        assert any((s.amount or 0) < 0 for s in signals), c.first_name
