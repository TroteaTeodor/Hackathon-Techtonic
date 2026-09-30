"""Advisor console endpoints. Every route requires the advisor role."""

from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import schemas
from app.analysis import analyze, detail, intervention_view, personalize_customer
from app.auth import require_advisor
from app.config import settings
from app.db import get_db
from app.models import Customer, InterventionRecord, MomentRecord, Signal

router = APIRouter(tags=["advisor"], dependencies=[Depends(require_advisor)])


def _latest_moments():
    latest = select(func.max(MomentRecord.id).label("id")).group_by(MomentRecord.customer_id).subquery()
    return select(MomentRecord).join(latest, MomentRecord.id == latest.c.id)


def _get_customer(db: Session, customer_id: int) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/customers", response_model=list[schemas.CustomerSummary])
def list_customers(
    moment: schemas.MomentKey | None = None, needs_review: bool = False,
    limit: int = Query(500, ge=1, le=1000), offset: int = Query(0, ge=0, le=100_000),
    db: Session = Depends(get_db),
):
    moments = {m.customer_id: m for m in db.scalars(_latest_moments())}
    reviews = dict(db.execute(
        select(InterventionRecord.customer_id, func.count())
        .where(InterventionRecord.status == "review").group_by(InterventionRecord.customer_id)
    ).all())
    rows = []
    for c in db.scalars(select(Customer).order_by(Customer.is_story.desc(), Customer.id)):
        m = moments.get(c.id)
        if moment and (not m or m.key != moment):
            continue
        if needs_review and not reviews.get(c.id):
            continue
        rows.append(schemas.CustomerSummary(
            id=c.id, name=f"{c.first_name} {c.last_name}", age=c.age, city=c.city,
            moment_key=m.key if m else None, moment_confidence=m.confidence if m else None,
            stress=m.stress if m else None, next_pinch_month=m.next_pinch_month if m else None,
            review_count=reviews.get(c.id, 0),
        ))
    return rows[offset: offset + limit]


@router.get("/customers/{customer_id}", response_model=schemas.CustomerDetail)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    return detail(db, _get_customer(db, customer_id))


@router.post("/customers/{customer_id}/signals", response_model=schemas.CustomerDetail)
def inject_signal(customer_id: int, body: schemas.SignalCreate, background: BackgroundTasks, db: Session = Depends(get_db)):
    customer = _get_customer(db, customer_id)
    count = db.scalar(select(func.count()).select_from(Signal).where(Signal.customer_id == customer.id))
    if count >= settings.max_signals_per_customer:
        raise HTTPException(status_code=409, detail="This customer has reached the signal limit")
    db.add(Signal(
        customer_id=customer.id, date=body.date or date.today(), kind=body.kind,
        description=body.description, amount=body.amount,
    ))
    if body.kind == "transaction":
        customer.balance = round(customer.balance + body.amount, 2)
    db.flush()
    analyze(db, customer)
    db.commit()
    background.add_task(personalize_customer, customer.id)  # Gemini wording arrives after the response
    return detail(db, customer)


@router.post("/interventions/{intervention_id}/decision", response_model=schemas.Intervention)
def decide(intervention_id: int, body: schemas.DecisionRequest, db: Session = Depends(get_db)):
    item = db.get(InterventionRecord, intervention_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Intervention not found")
    if item.status != "review":
        raise HTTPException(status_code=409, detail="Only interventions in review can be decided")
    item.decision = "approved" if body.decision == "approve" else "dismissed"
    item.status = "delivered" if body.decision == "approve" else "dismissed"
    db.commit()
    return intervention_view(item)


@router.get("/scale", response_model=schemas.ScaleStats)
def scale(db: Session = Depends(get_db)):
    moments = {k: 0 for k in schemas.MOMENT_KEYS}
    for m in db.scalars(_latest_moments()):
        moments[m.key] += 1
    statuses = {s: 0 for s in ("delivered", "review", "held", "dismissed")}
    for status, count in db.execute(select(InterventionRecord.status, func.count()).group_by(InterventionRecord.status)):
        statuses[status] = count

    ai = MomentRecord.source.in_(("jev", "gemini"))
    tokens_in, tokens_out, avg_cost = db.execute(
        select(func.avg(MomentRecord.input_tokens), func.avg(MomentRecord.output_tokens), func.avg(MomentRecord.cost_eur)).where(ai)
    ).one()
    # Until an AI analysis has run, use the configured estimate (it is shown as an assumption).
    tokens_in = float(tokens_in or settings.estimated_input_tokens_per_analysis)
    tokens_out = float(tokens_out or settings.estimated_output_tokens_per_analysis)
    cost = float(avg_cost) if avg_cost is not None else (
        tokens_in * settings.price_per_million_input_tokens_eur
        + tokens_out * settings.price_per_million_output_tokens_eur) / 1_000_000
    daily = settings.projection_customers * settings.daily_reevaluation_rate * cost
    handled = statuses["delivered"] + statuses["review"]
    return schemas.ScaleStats(
        population=db.scalar(select(func.count()).select_from(Customer)),
        moments=moments,
        interventions=statuses,
        automation_rate=round(statuses["delivered"] / handled, 3) if handled else 0.0,
        avg_tokens_per_analysis=round(tokens_in + tokens_out),
        avg_cost_per_analysis_eur=round(cost, 6),
        assumptions=schemas.ScaleAssumptions(
            customers=settings.projection_customers,
            daily_reevaluation_rate=settings.daily_reevaluation_rate,
            price_per_million_input_tokens_eur=settings.price_per_million_input_tokens_eur,
            price_per_million_output_tokens_eur=settings.price_per_million_output_tokens_eur,
        ),
        projected_daily_cost_eur=round(daily, 2),
        projected_monthly_cost_eur=round(daily * 30, 2),
    )
