"""Customer endpoints. The customer is always taken from the session (require_customer), never from the URL."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import insights, schemas
from app.analysis import overview, reject_moment, replan
from app.auth import require_customer
from app.db import get_db
from app.models import Customer, InterventionRecord, Signal

router = APIRouter(prefix="/me", tags=["customer"])


@router.get("/overview", response_model=schemas.CustomerOverview)
def get_overview(customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    return overview(db, customer)


@router.get("/transactions", response_model=list[schemas.Signal])
def get_transactions(
    limit: int = Query(40, ge=1, le=100),
    customer: Customer = Depends(require_customer), db: Session = Depends(get_db),
):
    # The customer's own account activity, newest first. Only transactions: searches, app events and
    # contacts are signals we read, not something the customer sees as a statement line.
    # Recurring detection needs the whole history, so classify all of it, then return the newest transactions.
    signals = list(db.scalars(select(Signal).where(Signal.customer_id == customer.id)))
    views = [v for v in insights.signal_views(signals) if v.kind == "transaction"]
    return sorted(views, key=lambda v: (v.date, v.id), reverse=True)[:limit]


@router.put("/preferences", response_model=schemas.CustomerOverview)
def update_preferences(body: schemas.PreferencesUpdate, customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    customer.proactivity = body.proactivity
    replan(db, customer)  # proactivity only affects the policy, so the detected moment is kept
    db.commit()
    return overview(db, customer)


@router.post("/moment/reject", response_model=schemas.CustomerOverview)
def reject(customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    reject_moment(db, customer)
    db.commit()
    return overview(db, customer)


@router.post("/interventions/{intervention_id}/feedback", response_model=schemas.CustomerOverview)
def feedback(
    intervention_id: int, body: schemas.FeedbackRequest,
    customer: Customer = Depends(require_customer), db: Session = Depends(get_db),
):
    # Scoped to the session's customer: someone else's intervention is indistinguishable from a missing one.
    item = db.scalar(select(InterventionRecord).where(
        InterventionRecord.id == intervention_id, InterventionRecord.customer_id == customer.id,
    ))
    if item is None or item.status != "delivered":
        raise HTTPException(status_code=404, detail="Intervention not found")
    item.feedback = body.feedback
    db.commit()
    return overview(db, customer)
