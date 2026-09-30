"""Run detection -> twin -> policy for one customer, persist it, and build API views."""

import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import insights, personalize, schemas
from app.detection import gemini as gemini_detector
from app.detection import LABELS, Detection, cap_confidence, detect, normalize
from app.interventions import STRESS_THRESHOLD, plan
from app.models import Customer, InterventionRecord, MomentRecord, Signal
from app.twin import analyse_history, build_twin, monthly_income


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
        cost_eur=detection.cost_eur,
        next_pinch_month=twin.pinch_points[0].month if twin.pinch_points else None,
    )
    db.add(record)
    _apply_plan(db, customer, detection, twin, signals)
    db.flush()
    return record


def _suggestion_status(customer, detection, line: str) -> tuple[str, str]:
    """Spending-based suggestions go through the same guardrails as every other card."""
    stressed = detection.stress >= STRESS_THRESHOLD or detection.key == "financial_stress"
    if stressed:
        return ("review", "Guardrail: support only, an advisor reviews") if line == "support" else \
               ("held", "Held: no sales while there are signs of financial difficulty")
    if line != "support" and not customer.marketing_consent:
        return "held", "Held: the customer hasn't given marketing consent"
    if line != "support" and customer.proactivity == "minimal":
        return "held", "Held: the customer chose 'minimal' proactivity"
    return "delivered", f"You allow offers and your proactivity is '{customer.proactivity}'"


def _suggestion_candidates(customer, detection, twin, signals):
    subs = insights.subscriptions(signals)
    spending = insights.spending(signals)
    surplus = sum(m.income - m.expenses for m in twin.months[:3]) / 3 if twin.months else 0.0
    ctx = personalize.build_context(customer, detection, spending, subs, twin, surplus)
    candidates = []
    for key in personalize.eligible_suggestions(ctx):
        item = personalize.suggestion_item(key, ctx)
        status, why = _suggestion_status(customer, detection, item["line"])
        candidates.append({**item, "status": status, "deliver_at": date.today(), "reasons": item["reasons"] + [why]})
    return ctx, candidates


def _apply_plan(db: Session, customer: Customer, detection, twin, signals) -> None:
    """Upsert interventions by key so IDs stay stable; keep customer feedback, advisor decisions and wording.

    Deterministic and fast (no AI): the policy decides what to show, and at most two spending suggestions are
    added. personalize_customer() later rewrites the wording with Gemini in the background.
    """
    existing = {i.key: i for i in db.scalars(select(InterventionRecord).where(InterventionRecord.customer_id == customer.id))}
    income = monthly_income(analyse_history(signals)[1])
    planned = plan(customer, detection, twin, date.today(), subs=insights.subscriptions(signals), income=income, signals=signals)

    _, candidates = _suggestion_candidates(customer, detection, twin, signals)
    showable = [c["key"] for c in candidates if c["status"] == "delivered"]
    kept = [k for k in existing if k in showable]  # keep earlier (possibly AI-chosen) picks when still valid
    picked = (kept + [k for k in showable if k not in kept])[: personalize.MAX_SUGGESTIONS]
    # Show the picked suggestions; keep held/review ones too, so advisors see what the guardrails stopped.
    planned += [c for c in candidates if c["status"] != "delivered" or c["key"] in picked]

    for item in planned:
        row = existing.get(item["key"])
        status = item["status"]
        decision = row.decision if row else None
        if decision == "dismissed":
            status = "dismissed"
        elif decision == "approved" and status == "review":
            status = "delivered"
        fields = {k: v for k, v in item.items() if k not in ("key", "status")}
        if row is not None and row.personalized:  # keep the personal wording the customer already saw
            fields["title"], fields["message"], fields["reasons"] = row.title, row.message, row.reasons
        if row is None:
            db.add(InterventionRecord(customer_id=customer.id, key=item["key"], status=status, **fields))
        else:
            row.status = status
            for name, value in fields.items():
                setattr(row, name, value)
    for key in existing.keys() - {i["key"] for i in planned}:
        db.delete(existing[key])


def keep_evidence(template: str, message: str) -> str:
    """The 'We noticed …' sentence names the real signal (the notary); it stays word for word."""
    if not template.startswith("We noticed"):
        return message
    first = re.split(r"(?<=[.!?])\s+", template, maxsplit=1)[0]
    if first in message:
        return message
    rest = re.sub(r"^We noticed[^.?!]*[.?!]\s*", "", message)
    return f"{first} {rest}".strip()


def personalize_customer(customer_id: int) -> bool:
    """Background step: Gemini Flash rewrites the visible cards and picks the best spending suggestions.

    Runs after the response (and in parallel at startup), so it never slows a request. Output is validated
    (personalize.validate); customers under financial stress are skipped. Returns True when copy was applied.
    """
    from app.db import SessionLocal

    with SessionLocal() as db:
        customer = db.get(Customer, customer_id)
        moment = current_moment(db, customer_id)
        if customer is None or moment is None:
            return False
        detection = _detection_from(moment)
        if detection.stress >= STRESS_THRESHOLD or detection.key == "financial_stress":
            return False  # never generated copy for customers in financial difficulty
        signals = customer_signals(db, customer_id)
        twin = build_twin(customer.balance, signals, moment.key, moment.confidence)
        ctx, candidates = _suggestion_candidates(customer, detection, twin, signals)
        showable = [c["key"] for c in candidates if c["status"] == "delivered"]
        rows = {i.key: i for i in interventions_of(db, customer_id)}
        income = monthly_income(analyse_history(signals)[1])
        templates = {i["key"]: i for i in plan(customer, detection, twin, date.today(), subs=insights.subscriptions(signals),
                                                income=income, signals=signals)}
        visible = [{"key": r.key, "title": templates[r.key]["title"], "message": templates[r.key]["message"], "cta": r.cta}
                   for r in rows.values()
                   if r.status in ("delivered", "review") and r.key in templates and not r.key.startswith("suggest_")]
        copy, tin, tout = personalize.write(ctx, visible, showable)
        if copy is None:
            return False

        _lock(db, customer)
        note = "Wording personalised by Gemini Flash from your categorised spending"
        for card in copy.cards:
            row = rows.get(card.key)
            if row is not None:
                row.title, row.message = card.title, keep_evidence(templates[card.key]["message"], card.message)
                row.reasons = [*templates[card.key]["reasons"], note]
                row.personalized = True
        if copy.suggestions:
            chosen = {s.key: s for s in copy.suggestions}
            for key, row in rows.items():
                if key.startswith("suggest_") and row.status == "delivered" and key not in chosen:
                    db.delete(row)
            for key, s in chosen.items():
                item = next(c for c in candidates if c["key"] == key)
                row = rows.get(key)
                if row is None:
                    row = InterventionRecord(customer_id=customer_id, key=key, status=item["status"],
                                             **{k: v for k, v in item.items() if k not in ("key", "status")})
                    db.add(row)
                row.message = s.message
                row.reasons = [*item["reasons"], "Picked for you by Gemini Flash from your categorised spending", note]
                row.personalized = True
        moment.cost_eur = (moment.cost_eur or 0) + gemini_detector.cost_eur(
            Detection("", 0, {}, 0, 0, "", "", input_tokens=tin, output_tokens=tout))
        db.commit()
        return True


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
    _apply_plan(db, customer, _detection_from(moment), build_twin(customer.balance, signals, moment.key, moment.confidence), signals)
    db.flush()


def respect_rejection(customer: Customer, detection: Detection) -> Detection:
    """If detection lands on the moment the customer rejected, drop it and take the next most likely one."""
    if not customer.rejected_moment or detection.key != customer.rejected_moment:
        return detection
    probs = normalize({k: (0.0 if k == customer.rejected_moment else v) for k, v in detection.probabilities.items()})
    key = max(probs, key=probs.get)
    detection.key, detection.confidence, detection.probabilities = key, probs[key], probs
    detection.rationale = f"{detection.rationale} (The customer told us '{LABELS[customer.rejected_moment].lower()}' isn't right.)"
    return detection


def analyze(db: Session, customer: Customer, use_ai: bool = True) -> MomentRecord:
    signals = customer_signals(db, customer.id)
    return persist(db, customer, signals, respect_rejection(customer, detect(customer, signals, use_ai=use_ai)))


def reject_moment(db: Session, customer: Customer) -> MomentRecord:
    """The customer says the detected moment is wrong: record that and recompute."""
    previous = current_moment(db, customer.id)
    if previous and previous.key not in ("no_clear_moment", "financial_stress"):
        customer.rejected_moment = previous.key
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
    probs, confidence = record.probabilities, record.confidence
    if record.source != "customer":  # a model is never 100% sure; older rows may still say 1.0
        probs = cap_confidence(probs)
        confidence = min(confidence, probs[record.key])
    return schemas.Moment(
        key=record.key, label=LABELS[record.key], confidence=confidence,
        probabilities=probs, stress=record.stress, receptiveness=record.receptiveness,
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
        status=i.status, deliver_at=i.deliver_at, reasons=i.reasons, feedback=i.feedback, cta=i.cta,
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
        subscriptions=insights.subscriptions(signals), spending=insights.spending(signals),
    )


SIGNALS_IN_DETAIL = 200


def detail(db: Session, customer: Customer) -> schemas.CustomerDetail:
    signals = customer_signals(db, customer.id)
    moment = current_moment(db, customer.id)
    views = {v.id: v for v in insights.signal_views(signals)}
    newest = sorted(signals, key=lambda s: (s.date, s.id), reverse=True)[:SIGNALS_IN_DETAIL]
    return schemas.CustomerDetail(
        customer=profile_view(customer),
        signals=[views[s.id] for s in newest],
        moment=moment_view(moment),
        twin=_twin(customer, signals, moment),
        interventions=[intervention_view(i) for i in interventions_of(db, customer.id)],
        subscriptions=insights.subscriptions(signals), spending=insights.spending(signals),
    )


def personalize_in_background(customer_ids) -> None:
    """Personalise several customers in parallel without blocking the caller (startup, batch jobs)."""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    ids = list(customer_ids)
    if not ids or not personalize.enabled():
        return

    def run():
        with ThreadPoolExecutor(max_workers=7) as pool:
            list(pool.map(personalize_customer, ids))

    threading.Thread(target=run, daemon=True, name="personalize").start()
