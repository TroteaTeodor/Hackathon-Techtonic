from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    age: Mapped[int] = mapped_column(Integer)
    city: Mapped[str] = mapped_column(String(50))
    marketing_consent: Mapped[bool] = mapped_column(Boolean)
    proactivity: Mapped[str] = mapped_column(String(20), default="balanced")
    balance: Mapped[float] = mapped_column(Float)
    is_story: Mapped[bool] = mapped_column(Boolean, default=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(String(200))
    amount: Mapped[float | None] = mapped_column(Float)


class MomentRecord(Base):
    """One row per analysis; the latest row per customer is the current moment."""

    __tablename__ = "moments"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    key: Mapped[str] = mapped_column(String(40))
    confidence: Mapped[float] = mapped_column(Float)
    probabilities: Mapped[dict] = mapped_column(JSON)
    stress: Mapped[float] = mapped_column(Float)
    receptiveness: Mapped[int] = mapped_column(Integer)
    rationale: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    next_pinch_month: Mapped[str | None] = mapped_column(String(7))
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InterventionRecord(Base):
    __tablename__ = "interventions"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    key: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(Text)
    line: Mapped[str] = mapped_column(String(20))
    channel: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    deliver_at: Mapped[date] = mapped_column(Date)
    reasons: Mapped[list] = mapped_column(JSON)
    feedback: Mapped[str | None] = mapped_column(String(20))
    # Advisor decision ("approved" / "dismissed"), kept across re-analysis.
    decision: Mapped[str | None] = mapped_column(String(20))
