import os

# Tests run against a separate database, with rules only (no AI calls) and a fixed demo password.
_base = os.environ["DATABASE_URL"]  # set by docker-compose from .env
os.environ["DATABASE_URL"] = _base.rsplit("/", 1)[0] + "/app_test"
os.environ["AI_ENABLED"] = "false"
os.environ["DEMO_PASSWORD"] = "test-demo-password"
os.environ["WRITE_RATE_LIMIT_PER_MINUTE"] = "100000"  # the suite makes many writes; limits are tested directly
os.environ.setdefault("SESSION_SECRET", "test-session-secret-that-is-long-enough-123")

import pytest  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

_admin = create_engine(_base, isolation_level="AUTOCOMMIT")
with _admin.connect() as conn:
    if not conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'app_test'")).scalar():
        conn.execute(text("CREATE DATABASE app_test"))
_admin.dispose()

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402,F401
from app.auth import login_limiter  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "test-demo-password"


@pytest.fixture(scope="session", autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture(scope="session")
def client(database):
    with TestClient(app) as c:  # lifespan seeds the database
        yield c


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture(autouse=True)
def reset_rate_limit():
    login_limiter.reset()
    yield
    login_limiter.reset()


def login(client, username: str) -> TestClient:
    client.cookies.clear()
    res = client.post("/auth/login", json={"username": username, "password": PASSWORD})
    assert res.status_code == 200, res.text
    return client


def customer_id(db, first_name: str) -> int:
    from sqlalchemy import select

    from app.models import Customer

    return db.scalar(select(Customer.id).where(Customer.first_name == first_name, Customer.is_story))
