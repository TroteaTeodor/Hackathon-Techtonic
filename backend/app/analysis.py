"""Run detection -> twin -> policy for one customer, persist it, and build API views."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.detection import LABELS, Detection, detect
from app.interventions import plan
from app.models import Customer, InterventionRecord, MomentRecord, Signal
from app.twin import build_twin


def customer_signals(db: Session, customer_id: int) -> list[Signal]:
    return list(db.scalars(select(Signal).where(Signal.customer_id == customer_id)))


def current_moment(db: Session, customer_id: int) -> MomentRecord | None:
    return db.scalar(
        select(MomentRecord).where(MomentRecord.customer_id == customer_id).order_by(MomentRecord.id.desc()).limit(1)
    )


def _lock(db: Session, customer: Customer) -> None:
    # Serialise analyses of the same customer so concurrent requests can't interleave intervention updates.
    db.execute(select(Customer.id).where(Customer.id == customer.id).with_for_update())


def persist(db: Session, customer: Customer, signals: list[Signal], detection: Detection) -> MomentRecord:
    _lock(db, customer)
    twin = build_twin(customer.balance, signals, detection.key, detection.confidence)
    record = MomentRecord(
        customer_id=customer.id,
        key=detection.key,
        confidence=detection.confidence,
        probabilities=detection.probabilities,
        stress=detection.stress,
        receptiveness=detection.receptiveness,
        rationale=detection.rationale,
        source=detection.source,
        input_tokens=detection.input_tokens,
        output_tokens=detection.output_tokens,
        next_pinch_month=twin.pinch_points[0].month if twin.pinch_points else None,
    )
    db.add(record)
    _apply_plan(db, customer, detection, twin)
    db.flush()
    return record


def _apply_plan(db: Session, customer: Customer, detection, twin) -> None:
    """Upsert interventions by key so IDs stay stable; keep customer feedback and advisor decisions."""
    existing = {i.key: i for i in db.scalars(select(InterventionRecord).where(InterventionRecord.customer_id == customer.id))}
    planned = plan(customer, detection, twin, date.today())
    for item in planned:
        row = existing.get(item["key"])
        status = item["status"]
        decision = row.decision if row else None
        if decision == "dismissed":
            status = "dismissed"
        elif decision == "approved" and status == "review":
            status = "delivered"
        fields = {k: v for k, v in item.items() if k not in ("key", "status")}
        if row is None:
            db.add(InterventionRecord(customer_id=customer.id, key=item["key"], status=status, **fields))
        else:
            row.status = status
            for name, value in fields.items():
                setattr(row, name, value)
    for key in existing.keys() - {i["key"] for i in planned}:
        db.delete(existing[key])


def _detection_from(record: MomentRecord) -> Detection:
    return Detection(
        key=record.key, confidence=record.confidence, probabilities=record.probabilities, stress=record.stress,
        receptiveness=record.receptiveness, rationale=record.rationale, source=record.source,
    )


def replan(db: Session, customer: Customer) -> None:
    """Re-run only the policy against the current moment (e.g. after a proactivity change). No new detection."""
    moment = current_moment(db, customer.id)
    if moment is None:
        analyze(db, customer)
        return
    _lock(db, customer)
    signals = customer_signals(db, customer.id)
    _apply_plan(db, customer, _detection_from(moment), build_twin(customer.balance, signals, moment.key, moment.confidence))
    db.flush()


def analyze(db: Session, customer: Customer, use_ai: bool = True) -> MomentRecord:
    signals = customer_signals(db, customer.id)
    return persist(db, customer, signals, detect(customer, signals, use_ai=use_ai))


def reject_moment(db: Session, customer: Customer) -> MomentRecord:
    """The customer says the detected moment is wrong: record that and recompute."""
    previous = current_moment(db, customer.id)
    probabilities = {k: 0.0 for k in schemas.MOMENT_KEYS}
    probabilities["no_clear_moment"] = 1.0
    detection = Detection(
        key="no_clear_moment", confidence=1.0, probabilities=probabilities,
        stress=previous.stress if previous else 0.0,
        receptiveness=previous.receptiveness if previous else 1,
        rationale="The customer told us this moment isn't right.", source="customer",
    )
    return persist(db, customer, customer_signals(db, customer.id), detection)


# ---------- views ----------

def moment_view(record: MomentRecord | None) -> schemas.Moment | None:
    if record is None:
        return None
    return schemas.Moment(
        key=record.key, label=LABELS[record.key], confidence=record.confidence,
        probabilities=record.probabilities, stress=record.stress, receptiveness=record.receptiveness,
        rationale=record.rationale, source=record.source, analyzed_at=record.analyzed_at,
    )


def profile_view(c: Customer) -> schemas.CustomerProfile:
    return schemas.CustomerProfile(
        id=c.id, first_name=c.first_name, last_name=c.last_name, age=c.age, city=c.city,
        marketing_consent=c.marketing_consent, proactivity=c.proactivity, balance=round(c.balance, 2),
    )


def intervention_view(i: InterventionRecord) -> schemas.Intervention:
    return schemas.Intervention(
        id=i.id, key=i.key, title=i.title, message=i.message, line=i.line, channel=i.channel,
        status=i.status, deliver_at=i.deliver_at, reasons=i.reasons, feedback=i.feedback,
    )


def _twin(customer: Customer, signals, moment: MomentRecord | None):
    return build_twin(customer.balance, signals, moment.key if moment else None, moment.confidence if moment else None)


def interventions_of(db: Session, customer_id: int) -> list[InterventionRecord]:
    return list(db.scalars(
        select(InterventionRecord).where(InterventionRecord.customer_id == customer_id).order_by(InterventionRecord.id)
    ))


def overview(db: Session, customer: Customer) -> schemas.CustomerOverview:
    signals = customer_signals(db, customer.id)
    moment = current_moment(db, customer.id)
    today = date.today()
    visible = [
        intervention_view(i) for i in interventions_of(db, customer.id)
        if i.status == "delivered" and i.feedback != "not_relevant" and i.deliver_at <= today
    ]
    return schemas.CustomerOverview(
        customer=profile_view(customer), moment=moment_view(moment),
        twin=_twin(customer, signals, moment), interventions=visible,
    )


SIGNALS_IN_DETAIL = 60


def detail(db: Session, customer: Customer) -> schemas.CustomerDetail:
    signals = customer_signals(db, customer.id)
    moment = current_moment(db, customer.id)
    newest = sorted(signals, key=lambda s: (s.date, s.id), reverse=True)[:SIGNALS_IN_DETAIL]
    return schemas.CustomerDetail(
        customer=profile_view(customer),
        signals=[schemas.Signal(id=s.id, date=s.date, description=s.description, amount=s.amount, kind=s.kind) for s in newest],
        moment=moment_view(moment),
        twin=_twin(customer, signals, moment),
        interventions=[intervention_view(i) for i in interventions_of(db, customer.id)],
    )
