import pytest
from sqlalchemy import select

from app import analysis
from app.models import InterventionRecord
from tests.conftest import PASSWORD, customer_id, login


def test_login_sets_http_only_cookie(client):
    client.cookies.clear()
    res = client.post("/auth/login", json={"username": "sara", "password": PASSWORD})
    assert res.status_code == 200 and res.json() == {"role": "customer", "display_name": "Sara Janssens"}
    cookie = res.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "max-age=28800" in cookie


@pytest.mark.parametrize("username,password", [("sara", "wrong"), ("nobody", PASSWORD)])
def test_bad_login_is_generic_401(client, username, password):
    res = client.post("/auth/login", json={"username": username, "password": password})
    assert res.status_code == 401 and res.json() == {"detail": "Invalid username or password"}


def test_sixth_failed_attempt_is_rate_limited(client):
    for _ in range(5):
        assert client.post("/auth/login", json={"username": "marc", "password": "nope"}).status_code == 401
    assert client.post("/auth/login", json={"username": "marc", "password": PASSWORD}).status_code == 429


def test_logout_clears_cookie(client):
    login(client, "sara")
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/me/overview").status_code == 401


@pytest.mark.parametrize("path", ["/auth/me", "/me/overview", "/customers", "/customers/1", "/scale"])
def test_no_cookie_is_401(client, path):
    client.cookies.clear()
    assert client.get(path).status_code == 401


def test_tampered_cookie_is_401(client):
    client.cookies.clear()
    client.cookies.set("session", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.forged")
    assert client.get("/me/overview").status_code == 401


def test_customer_cannot_use_advisor_endpoints(client):
    login(client, "sara")
    assert client.get("/customers").status_code == 403
    assert client.get("/scale").status_code == 403


def test_advisor_cannot_use_customer_endpoints(client):
    login(client, "advisor")
    assert client.get("/me/overview").status_code == 403


def test_customer_overview_shows_only_delivered(client):
    login(client, "sara")
    body = client.get("/me/overview").json()
    assert body["customer"]["first_name"] == "Sara"
    assert body["moment"]["key"] == "moving_home"
    assert body["interventions"] and all(i["status"] == "delivered" for i in body["interventions"])


def test_idor_feedback_on_other_customers_intervention_is_404(client, db):
    julie = customer_id(db, "Julie")
    other = db.scalar(select(InterventionRecord).where(InterventionRecord.customer_id == julie))
    before = other.feedback
    login(client, "sara")
    res = client.post(f"/me/interventions/{other.id}/feedback", json={"feedback": "not_relevant"})
    assert res.status_code == 404
    db.refresh(other)
    assert other.feedback == before


def test_not_relevant_hides_the_card(client):
    login(client, "sara")
    card = client.get("/me/overview").json()["interventions"][0]
    body = client.post(f"/me/interventions/{card['id']}/feedback", json={"feedback": "not_relevant"}).json()
    assert card["id"] not in [i["id"] for i in body["interventions"]]


def test_minimal_proactivity_removes_moment_cards(client):
    login(client, "lien")
    body = client.put("/me/preferences", json={"proactivity": "minimal"}).json()
    assert body["customer"]["proactivity"] == "minimal"
    assert not [i for i in body["interventions"] if i["key"].startswith("growing_family")]


def test_customer_can_reject_moment(client):
    login(client, "pieter")
    body = client.post("/me/moment/reject").json()
    assert body["moment"]["key"] == "no_clear_moment" and body["moment"]["source"] == "customer"


def test_inject_notary_changes_jan(client, db):
    jan = customer_id(db, "Jan")
    login(client, "advisor")
    assert client.get(f"/customers/{jan}").json()["moment"]["key"] == "no_clear_moment"
    res = client.post(f"/customers/{jan}/signals", json={
        "kind": "transaction", "description": "Notary deposit — Notaris Peeters", "amount": -15000})
    assert res.status_code == 200
    body = res.json()
    assert body["moment"]["key"] == "moving_home"
    assert body["signals"][0]["description"] == "Notary deposit — Notaris Peeters"
    assert body["customer"]["balance"] == 17500


@pytest.mark.parametrize("payload", [
    {"kind": "telepathy", "description": "x"},
    {"kind": "search", "description": ""},
    {"kind": "search", "description": "x" * 201},
    {"kind": "transaction", "description": "No amount"},
])
def test_invalid_signal_is_422(client, db, payload):
    login(client, "advisor")
    assert client.post(f"/customers/{customer_id(db, 'Jan')}/signals", json=payload).status_code == 422


def test_advisor_approves_review_item(client, db):
    login(client, "advisor")
    julie = customer_id(db, "Julie")
    item = next(i for i in client.get(f"/customers/{julie}").json()["interventions"] if i["status"] == "review")
    res = client.post(f"/interventions/{item['id']}/decision", json={"decision": "approve"})
    assert res.status_code == 200 and res.json()["status"] == "delivered"
    login(client, "julie")
    assert item["id"] in [i["id"] for i in client.get("/me/overview").json()["interventions"]]


def test_list_filters(client):
    login(client, "advisor")
    everyone = client.get("/customers").json()
    assert len(everyone) >= 207
    assert all(c["moment_key"] == "moving_home" for c in client.get("/customers?moment=moving_home").json())
    assert all(c["review_count"] > 0 for c in client.get("/customers?needs_review=true").json())


def test_listing_does_not_rerun_detection(client, monkeypatch):
    calls = []
    monkeypatch.setattr(analysis, "detect", lambda *a, **k: calls.append(1))
    login(client, "advisor")
    client.get("/customers")
    client.get("/customers")
    assert calls == []


def test_scale_projection(client):
    login(client, "advisor")
    body = client.get("/scale").json()
    assert body["population"] >= 207
    assert body["assumptions"]["customers"] == 2_300_000
    assert body["projected_monthly_cost_eur"] == pytest.approx(body["projected_daily_cost_eur"] * 30, abs=1)


def test_cors_only_for_known_origin(client):
    ok = client.options("/auth/me", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    bad = client.options("/auth/me", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "access-control-allow-origin" not in bad.headers


def test_missing_or_short_session_secret_fails_startup(monkeypatch):
    from pydantic import ValidationError

    from app.config import Settings

    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with pytest.raises(ValidationError):
        Settings()
    with pytest.raises(ValidationError):
        Settings(session_secret="too-short")


def test_login_limiter_does_not_grow_on_checks():
    from app.auth import LoginRateLimiter

    limiter = LoginRateLimiter()
    for n in range(100):
        limiter.blocked(f"user{n}", "1.2.3.4")
    assert len(limiter._failures) == 0


def test_preferences_keep_a_rejected_moment_and_ids(client):
    login(client, "ahmed")
    rejected = client.post("/me/moment/reject").json()
    assert rejected["moment"]["key"] == "no_clear_moment"
    after = client.put("/me/preferences", json={"proactivity": "proactive"}).json()
    assert after["moment"]["key"] == "no_clear_moment" and after["moment"]["source"] == "customer"


def test_intervention_ids_are_stable_across_replans(client, db):
    login(client, "advisor")
    julie = customer_id(db, "Julie")
    before = {i["key"]: i["id"] for i in client.get(f"/customers/{julie}").json()["interventions"]}
    login(client, "julie")
    client.put("/me/preferences", json={"proactivity": "proactive"})
    login(client, "advisor")
    after = {i["key"]: i["id"] for i in client.get(f"/customers/{julie}").json()["interventions"]}
    assert before == after


def test_future_deliveries_are_not_shown_yet(client):
    from datetime import date

    login(client, "sara")
    for item in client.get("/me/overview").json()["interventions"]:
        assert date.fromisoformat(item["deliver_at"]) <= date.today()


def test_validation_errors_have_a_string_detail(client, db):
    login(client, "advisor")
    res = client.post(f"/customers/{customer_id(db, 'Jan')}/signals", json={"kind": "transaction", "description": "No amount"})
    assert res.status_code == 422
    assert isinstance(res.json()["detail"], str) and "amount" in res.json()["detail"]


def test_rejected_moment_survives_a_new_signal(client, db):
    login(client, "lien")
    assert client.post("/me/moment/reject").json()["moment"]["key"] == "no_clear_moment"
    login(client, "advisor")
    lien = customer_id(db, "Lien")
    body = client.post(f"/customers/{lien}/signals", json={
        "kind": "transaction", "description": "Kruidvat — baby wipes", "amount": -12}).json()
    assert body["moment"]["key"] != "growing_family"
    assert "isn't right" in body["moment"]["rationale"]


def test_oversized_body_is_rejected(client):
    login(client, "advisor")
    res = client.post("/customers/1/signals", content=b"x" * (70 * 1024), headers={"content-type": "application/json"})
    assert res.status_code == 413


def test_write_rate_limit(monkeypatch):
    from app.limits import WriteRateLimiter

    limiter = WriteRateLimiter(per_minute=3)
    assert [limiter.allow("1.2.3.4") for _ in range(4)] == [True, True, True, False]
    assert limiter.allow("5.6.7.8")


def test_validation_errors_are_capped(client, db):
    login(client, "advisor")
    res = client.post(f"/customers/{customer_id(db, 'Jan')}/signals", json=[{"x": i} for i in range(500)])
    assert res.status_code == 422 and len(res.json()["detail"]) < 2000
