from datetime import date, timedelta
from types import SimpleNamespace

from app.twin import build_twin
from tests.helpers import story_signals

TODAY = date(2026, 9, 30)


def tx(d, desc, amount, i=0):
    return SimpleNamespace(id=i, date=d, kind="transaction", description=desc, amount=amount)


def test_shape_is_twelve_consecutive_months():
    twin = build_twin(1000, story_signals("jan", TODAY))
    assert [m.month for m in twin.months][:2] == ["2026-10", "2026-11"]
    assert len(twin.months) == 12 and twin.months[-1].month == "2027-09"


def test_monthly_salary_is_recurring():
    signals = [tx(date(2026, m, 1), "Salary — Acme", 3000, m) for m in range(1, 10)]
    twin = build_twin(0, signals)
    assert all(any(e.label == "Salary — Acme" and e.source == "recurring" for e in m.events) for m in twin.months)


def test_yearly_premium_is_scheduled_in_the_same_month():
    signals = [tx(date(2026, m, 1), "Salary — Acme", 3000, m) for m in range(1, 10)]
    signals.append(tx(date(2026, 3, 14), "Car insurance — KBC", -640, 99))
    twin = build_twin(0, signals)
    march = next(m for m in twin.months if m.month == "2027-03")
    assert any(e.label == "Car insurance — KBC" and e.amount == -640 and e.source == "scheduled" for e in march.events)
    assert sum(1 for m in twin.months for e in m.events if e.label == "Car insurance — KBC") == 1


def test_recent_one_off_is_not_projected():
    signals = [tx(date(2026, m, 1), "Salary — Acme", 3000, m) for m in range(1, 10)]
    signals.append(tx(TODAY - timedelta(days=5), "Notary deposit — Notaris Peeters", -15000, 99))
    twin = build_twin(20000, signals)
    assert not any("Notary deposit" in e.label for m in twin.months for e in m.events)


def test_moving_home_changes_the_future():
    signals = story_signals("sara", TODAY)
    plain = build_twin(9800, signals)
    moved = build_twin(9800, signals, "moving_home", 0.87)
    labels = {e.label for m in moved.months for e in m.events if e.source == "moment"}
    assert {"Notary fees (estimate)", "Moving costs (estimate)", "Mortgage payment — KBC home loan (estimate)"} <= labels
    assert [m.balance for m in plain.months] != [m.balance for m in moved.months]
    # Rent is replaced by the mortgage from the third month on.
    assert not any(e.label.startswith("Rent") for e in moved.months[2].events)


def test_low_confidence_adds_no_moment_events():
    twin = build_twin(9800, story_signals("sara", TODAY), "moving_home", 0.4)
    assert not any(e.source == "moment" for m in twin.months for e in m.events)


def test_pinch_point_names_the_notary_fees():
    twin = build_twin(9800, story_signals("sara", TODAY), "moving_home", 0.87)
    assert [p.month for p in twin.pinch_points] == ["2026-11"]
    assert "Notary fees" in twin.pinch_points[0].reason
    assert twin.pinch_points[0].balance < 250
