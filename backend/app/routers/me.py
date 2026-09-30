"""Customer endpoints. The customer is always taken from the session (require_customer), never from the URL."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import schemas
from app.analysis import analyze, overview, reject_moment
from app.auth import require_customer
from app.db import get_db
from app.models import Customer, InterventionRecord

router = APIRouter(prefix="/me", tags=["customer"])


@router.get("/overview", response_model=schemas.CustomerOverview)
def get_overview(customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    return overview(db, customer)


@router.put("/preferences", response_model=schemas.CustomerOverview)
def update_preferences(body: schemas.PreferencesUpdate, customer: Customer = Depends(require_customer), db: Session = Depends(get_db)):
    customer.proactivity = body.proactivity
    analyze(db, customer)
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
