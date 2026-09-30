"""Synthetic customers: 7 scripted story customers plus a deterministic generated population.

All names, merchants and amounts are fictitious. No real personal data.
"""

import logging
import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analysis import persist
from app.auth import hash_password
from app.config import settings
from app.detection import detect
from app.models import Customer, Signal, User

logger = logging.getLogger(__name__)

POPULATION_SIZE = 200
POPULATION_SEED = 42


@dataclass
class Story:
    username: str
    first_name: str
    last_name: str
    age: int
    city: str
    balance: float
    consent: bool
    proactivity: str
    monthly: list  # (description, amount, day_of_month, times_per_month)
    yearly: list = field(default_factory=list)  # (description, amount, month, day)
    recent: list = field(default_factory=list)  # (days_ago, kind, description, amount)
    history_only: list = field(default_factory=list)  # (description, amount, day, first_month_ago, last_month_ago)
    label: str | None = None  # the moment the generator scripted (ground truth for the evals)


def _months_back(today: date, n: int = 12):
    y, m = today.year, today.month
    for i in range(n):
        yy, mm = divmod(y * 12 + (m - 1) - i, 12)
        yield yy, mm + 1, i


def _history(story: Story, today: date, rng: random.Random) -> list[tuple]:
    rows = []
    for year, month, ago in _months_back(today):
        for desc, amount, day, times in story.monthly:
            for t in range(times):
                d = date(year, month, min(28, day + t * 7))
                if d > today:
                    continue
                value = amount if times == 1 else round(amount * rng.uniform(0.85, 1.15), 2)
                rows.append((d, "transaction", desc, value))
        for desc, amount, day, first_ago, last_ago in story.history_only:
            if last_ago <= ago <= first_ago:
                rows.append((date(year, month, day), "transaction", desc, amount))
    for desc, amount, month, day in story.yearly:
        year = today.year if (month, day) <= (today.month, today.day) else today.year - 1
        rows.append((date(year, month, day), "transaction", desc, amount))
    for days_ago, kind, desc, amount in story.recent:
        rows.append((today - timedelta(days=days_ago), kind, desc, amount))
    return rows


def _base(salary_desc, salary, rent_desc, rent, energy_desc, energy, telecom_desc, telecom, groceries_desc, groceries, card):
    return [
        (salary_desc, salary, 1, 1),
        (rent_desc, -rent, 3, 1),
        (energy_desc, -energy, 20, 1),
        (telecom_desc, -telecom, 15, 1),
        (groceries_desc, -groceries / 4, 2, 4),
        ("Card payment — Bancontact", -card / 3, 6, 3),
    ]


STORIES = [
    Story(
        "sara", "Sara", "Janssens", 31, "Leuven", 9800, True, "balanced",
        _base("Salary — Barco NV", 3100, "Rent — Immo Vandenberghe", 950, "Energy — Engie", 140,
              "Telecom — Proximus", 55, "Groceries — Colruyt", 520, 600) + [("Transport — NMBS", -70, 5, 1)],
        yearly=[("Home contents insurance — KBC", -180, 1, 10), ("Holiday pay — Barco NV", 2300, 5, 28)],
        recent=[
            (6, "app_event", "Opened the mortgage simulator (3 times this week)", None),
            (8, "search", "Searched the app for 'home insurance new apartment'", None),
            (12, "transaction", "Notary deposit — Notaris Peeters", -15000),
            (15, "contact", "Asked the chatbot: 'How long does a mortgage approval take?'", None),
            (20, "search", "Immoweb — 2-bedroom apartments in Leuven", None),
        ],
    ),
    Story(
        "lien", "Lien", "Wouters", 29, "Gent", 2600, True, "balanced",
        _base("Salary — UZ Gent", 2800, "Rent — Woonpunt Gent", 850, "Energy — Luminus", 120,
              "Telecom — Telenet", 60, "Groceries — Delhaize", 440, 450),
        yearly=[("Holiday pay — UZ Gent", 2000, 5, 28)],
        recent=[
            (5, "transaction", "Dreambaby — stroller", -429),
            (9, "transaction", "Kruidvat — baby care products", -64),
            (11, "search", "Searched 'parental leave rules Belgium'", None),
            (13, "app_event", "Opened the child savings account page", None),
            (25, "transaction", "Prenatal — maternity clothes", -89),
        ],
    ),
    Story(
        "ahmed", "Ahmed", "El Amrani", 23, "Antwerpen", 1450, False, "balanced",
        [("Telecom — Mobile Vikings", -20, 15, 1), ("Groceries — Aldi", -160 / 3, 4, 3), ("Card payment — Bancontact", -60, 9, 3)],
        history_only=[("Student job — Delhaize", 450, 28, 11, 2)],
        recent=[
            (8, "transaction", "Salary — Accenture Belgium", 2400),
            (7, "app_event", "Updated employer in profile: Accenture Belgium", None),
            (6, "search", "Searched 'first salary taxes'", None),
            (4, "contact", "Asked about salary account switching", None),
        ],
    ),
    Story(
        "marc", "Marc", "Dubois", 63, "Namur", 21000, True, "proactive",
        _base("Salary — SPF Finances", 3900, "Home loan instalment — KBC", 600, "Energy — Engie", 180,
              "Telecom — Proximus", 70, "Groceries — Carrefour", 600, 660),
        yearly=[("Car insurance — KBC", -720, 10, 12), ("Holiday pay — SPF Finances", 2900, 5, 28)],
        recent=[
            (5, "search", "Searched 'pension calculation mypension.be'", None),
            (10, "contact", "Asked an advisor about early retirement options", None),
        ],
    ),
    Story(
        "julie", "Julie", "Maes", 41, "Hasselt", -420, True, "balanced",
        _base("Salary — part-time, Colruyt Group", 1900, "Rent — private landlord", 1050, "Energy — Fluvius", 130,
              "Telecom — Proximus", 65, "Groceries — Aldi", 360, 300),
        recent=[
            (3, "transaction", "Overdraft interest — KBC", -38.4),
            (4, "search", "Searched 'payment plan energy bill'", None),
            (6, "transaction", "Returned direct debit — Fluvius", 130),
            (8, "contact", "Payment reminder received — Proximus", None),
            (10, "transaction", "Collection agency — Fairway", -120),
            (14, "transaction", "Cash advance — credit card", -300),
        ],
    ),
    Story(
        "pieter", "Pieter", "De Smet", 37, "Brugge", 3900, True, "balanced",
        _base("Salary — Sioen Industries", 3300, "Rent — Immo Brugge", 900, "Energy — Engie", 150,
              "Telecom — Orange", 60, "Groceries — Colruyt", 500, 540),
        recent=[
            (3, "search", "Searched 'car insurance quote'", None),
            (4, "app_event", "Opened the car loan simulator", None),
            (6, "search", "Autoscout24 — used Volvo XC40", None),
            (9, "contact", "Dealer quote received — Volvo Brugge", None),
        ],
    ),
    Story(
        "jan", "Jan", "Claes", 45, "Mechelen", 32500, True, "proactive",
        _base("Salary — Telenet", 3450, "Rent — Woonhaven", 890, "Energy — Luminus", 160,
              "Telecom — Telenet", 65, "Groceries — Aldi", 610, 700) + [("Fuel — TotalEnergies", -70, 8, 2)],
        yearly=[("Car insurance — KBC", -640, 3, 14), ("Holiday pay — Telenet", 2500, 5, 28)],
        recent=[(5, "app_event", "Checked account balance", None)],
    ),
]

FIRST = ["Lucas", "Emma", "Noah", "Olivia", "Arthur", "Louise", "Jules", "Mila", "Louis", "Elena", "Victor", "Lena",
         "Mathis", "Nora", "Finn", "Julia", "Adam", "Marie", "Liam", "Ella", "Rayan", "Zoë", "Thomas", "Laura",
         "Wout", "Fien", "Bram", "Hanne", "Youssef", "Ines"]
LAST = ["Peeters", "Janssens", "Maes", "Jacobs", "Mertens", "Willems", "Claes", "Goossens", "Wouters", "De Smet",
        "Dubois", "Lambert", "Dupont", "Vermeulen", "Hermans", "Aerts", "Michiels", "Desmet", "Martens", "Leclercq"]
CITIES = ["Antwerpen", "Gent", "Brussel", "Leuven", "Brugge", "Mechelen", "Hasselt", "Aalst", "Kortrijk", "Liège",
          "Namur", "Charleroi", "Genk", "Oostende", "Sint-Niklaas"]

MOMENT_SIGNALS = {
    "moving_home": [("search", "Immoweb — houses for sale", None), ("transaction", "Notary deposit — Notaris Verbeke", -12000),
                    ("app_event", "Opened the mortgage simulator", None), ("search", "Searched 'home insurance'", None)],
    "growing_family": [("transaction", "Dreambaby — baby bed", -249), ("search", "Searched 'parental leave'", None),
                       ("transaction", "Prenatal — baby clothes", -75)],
    "new_job": [("app_event", "Updated employer in profile", None), ("search", "Searched 'first salary taxes'", None),
                ("contact", "Asked about an employment contract certificate", None)],
    "approaching_retirement": [("search", "Searched 'pension calculation'", None),
                               ("contact", "Asked about early retirement", None)],
    "buying_car": [("search", "Autoscout24 — used cars", None), ("app_event", "Opened the car loan simulator", None),
                   ("contact", "Dealer quote received", None)],
    "travel_abroad": [("transaction", "Brussels Airlines — tickets", -640), ("transaction", "Booking.com — hotel", -420),
                      ("search", "Searched 'travel insurance'", None)],
    "financial_stress": [("transaction", "Returned direct debit — Engie", 140), ("transaction", "Overdraft interest — KBC", -31),
                         ("contact", "Payment reminder received", None), ("transaction", "Collection agency — Intrum", -95)],
}
MIX = [("no_clear_moment", 38), ("new_job", 11), ("travel_abroad", 10), ("moving_home", 9), ("growing_family", 8),
       ("buying_car", 8), ("approaching_retirement", 8), ("financial_stress", 8)]


def _population_story(rng: random.Random, n: int) -> Story:
    moment = rng.choices([m for m, _ in MIX], weights=[w for _, w in MIX])[0]
    salary = rng.randrange(2000, 4600, 50)
    rent = rng.randrange(650, 1250, 10)
    story = Story(
        f"pop{n}", rng.choice(FIRST), rng.choice(LAST),
        rng.randint(58, 66) if moment == "approaching_retirement" else rng.randint(21, 64),
        rng.choice(CITIES),
        float(rng.randrange(-900, 300, 10) if moment == "financial_stress" else rng.randrange(500, 26000, 50)),
        rng.random() < 0.8, rng.choices(["minimal", "balanced", "proactive"], weights=[15, 60, 25])[0],
        _base("Salary — employer", salary, "Rent — landlord", rent, "Energy — supplier", rng.randrange(90, 220, 5),
              "Telecom — provider", rng.randrange(30, 90, 5), "Groceries — supermarket", rng.randrange(350, 750, 10),
              rng.randrange(200, 800, 10)),
        label=moment,
    )
    if moment != "no_clear_moment":
        pool = MOMENT_SIGNALS[moment]
        for kind, desc, amount in rng.sample(pool, rng.randint(1, len(pool))):
            story.recent.append((rng.randint(1, 30), kind, desc, amount))
    return story


def _insert(db: Session, story: Story, is_story: bool, rng: random.Random) -> tuple[Customer, list[Signal]]:
    customer = Customer(
        first_name=story.first_name, last_name=story.last_name, age=story.age, city=story.city,
        marketing_consent=story.consent, proactivity=story.proactivity, balance=story.balance, is_story=is_story,
    )
    db.add(customer)
    db.flush()
    signals = [
        Signal(customer_id=customer.id, date=d, kind=kind, description=desc, amount=amount)
        for d, kind, desc, amount in _history(story, date.today(), rng)
    ]
    db.add_all(signals)
    db.flush()
    return customer, signals


def seed(db: Session, use_ai: bool = True) -> None:
    """Idempotent: story customers, population and demo users are only created when missing."""
    if not db.scalar(select(func.count()).select_from(Customer).where(Customer.is_story)):
        created = [(story, *_insert(db, story, True, random.Random(story.username))) for story in STORIES]
        # Story customers are analysed with Gemini when configured (in parallel), else with rules.
        with ThreadPoolExecutor(max_workers=7) as pool:
            detections = list(pool.map(lambda row: detect(row[1], row[2], use_ai=use_ai), created))
        for (story, customer, signals), detection in zip(created, detections):
            persist(db, customer, signals, detection)
            logger.info("Seeded %s: %s (%.2f, %s)", story.first_name, detection.key, detection.confidence, detection.source)
        db.commit()

    if db.scalar(select(func.count()).select_from(Customer).where(~Customer.is_story)) < POPULATION_SIZE:
        rng = random.Random(POPULATION_SEED)
        for n in range(POPULATION_SIZE):
            story = _population_story(rng, n)
            customer, signals = _insert(db, story, False, rng)
            persist(db, customer, signals, detect(customer, signals, use_ai=False))
        db.commit()

    _seed_users(db)


def _seed_users(db: Session) -> None:
    if not settings.demo_password:
        logger.warning("DEMO_PASSWORD is not set: demo accounts were not created")
        return
    existing = set(db.scalars(select(User.username)))
    story_customers = {c.first_name.lower(): c.id for c in db.scalars(select(Customer).where(Customer.is_story))}
    if "advisor" not in existing:
        db.add(User(username="advisor", password_hash=hash_password(settings.demo_password), role="advisor"))
    for story in STORIES:
        if story.username not in existing:
            db.add(User(
                username=story.username, password_hash=hash_password(settings.demo_password),
                role="customer", customer_id=story_customers[story.first_name.lower()],
            ))
    db.commit()
