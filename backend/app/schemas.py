"""API contract. Mirrors frontend/src/lib/types.ts; the fixtures in frontend/src/mocks must validate."""

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Role = Literal["customer", "advisor"]
MomentKey = Literal[
    "moving_home",
    "growing_family",
    "new_job",
    "approaching_retirement",
    "buying_car",
    "travel_abroad",
    "financial_stress",
    "no_clear_moment",
]
MOMENT_KEYS: tuple[str, ...] = MomentKey.__args__
Proactivity = Literal["minimal", "balanced", "proactive"]
SignalKind = Literal["transaction", "app_event", "search", "contact"]
InterventionStatus = Literal["delivered", "review", "held", "dismissed"]
TransactionCategory = Literal[
    "income", "housing", "energy", "telecom", "groceries", "transport", "subscriptions", "entertainment", "dining",
    "shopping", "health", "insurance", "travel", "family", "loans", "fees", "savings", "other",
]


class Me(BaseModel):
    role: Role
    display_name: str


class CustomerProfile(BaseModel):
    id: int
    first_name: str
    last_name: str
    age: int
    city: str
    marketing_consent: bool
    proactivity: Proactivity
    balance: float


class Signal(BaseModel):
    id: int
    date: dt.date
    description: str
    amount: float | None
    kind: SignalKind
    category: TransactionCategory | None  # transactions only
    recurring: bool  # the charge repeats monthly (or yearly, for periodic payments)


class PriceChange(BaseModel):
    before: float
    after: float


class Subscription(BaseModel):
    name: str
    monthly_amount: float
    yearly_amount: float
    since: str = Field(pattern=r"^\d{4}-\d{2}$")
    last_charged: dt.date
    price_change: PriceChange | None


class CategorySpend(BaseModel):
    category: TransactionCategory
    label: str
    monthly_average: float
    share: float = Field(ge=0, le=1)
    recurring_share: float = Field(ge=0, le=1)


class SignalCreate(BaseModel):
    kind: SignalKind
    description: str = Field(min_length=1, max_length=200)
    amount: float | None = None
    date: dt.date | None = None

    @field_validator("description")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("description must not be blank")
        return value.strip()

    @model_validator(mode="after")
    def amount_matches_kind(self):
        if self.kind == "transaction" and self.amount is None:
            raise ValueError("transactions need an amount")
        if self.kind != "transaction" and self.amount is not None:
            raise ValueError("only transactions have an amount")
        if self.date and self.date > dt.date.today():
            raise ValueError("date cannot be in the future")
        return self


class Moment(BaseModel):
    key: MomentKey
    label: str
    confidence: float = Field(ge=0, le=1)
    probabilities: dict[MomentKey, float]
    stress: float = Field(ge=0, le=1)
    receptiveness: Literal[0, 1, 2]
    rationale: str
    source: Literal["jev", "gemini", "rules", "customer"]
    analyzed_at: dt.datetime

    @field_validator("probabilities")
    @classmethod
    def complete_distribution(cls, value: dict[str, float]) -> dict[str, float]:
        if set(value) != set(MOMENT_KEYS):
            raise ValueError("probabilities must contain every moment key")
        if abs(sum(value.values()) - 1) > 0.01:
            raise ValueError("probabilities must sum to 1")
        return value


class TwinEvent(BaseModel):
    label: str
    amount: float
    kind: Literal["income", "expense"]
    source: Literal["recurring", "scheduled", "moment"]


class TwinMonth(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    income: float
    expenses: float
    balance: float
    events: list[TwinEvent]


class PinchPoint(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    balance: float
    reason: str


class Twin(BaseModel):
    start_balance: float
    months: list[TwinMonth] = Field(min_length=12, max_length=12)
    pinch_points: list[PinchPoint]


class Intervention(BaseModel):
    id: int
    key: str
    title: str
    message: str
    line: Literal["banking", "insurance", "investing", "support"]
    channel: Literal["app", "email", "advisor"]
    status: InterventionStatus
    deliver_at: dt.date
    reasons: list[str]
    feedback: Literal["helpful", "not_relevant"] | None
    cta: str | None  # label of the card's one direct action, e.g. "Get home insurance"


class CustomerOverview(BaseModel):
    customer: CustomerProfile
    moment: Moment | None
    twin: Twin
    interventions: list[Intervention]
    subscriptions: list[Subscription]
    spending: list[CategorySpend]


class CustomerSummary(BaseModel):
    id: int
    name: str
    age: int
    city: str
    moment_key: MomentKey | None
    moment_confidence: float | None
    stress: float | None
    next_pinch_month: str | None
    review_count: int


class CustomerDetail(BaseModel):
    customer: CustomerProfile
    signals: list[Signal]
    moment: Moment | None
    twin: Twin
    interventions: list[Intervention]
    subscriptions: list[Subscription]
    spending: list[CategorySpend]


class ScaleAssumptions(BaseModel):
    customers: int
    daily_reevaluation_rate: float
    price_per_million_input_tokens_eur: float
    price_per_million_output_tokens_eur: float


class ScaleStats(BaseModel):
    population: int
    moments: dict[MomentKey, int]
    interventions: dict[InterventionStatus, int]
    automation_rate: float
    avg_tokens_per_analysis: float
    avg_cost_per_analysis_eur: float
    assumptions: ScaleAssumptions
    projected_daily_cost_eur: float
    projected_monthly_cost_eur: float


# Request bodies
class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)


class PreferencesUpdate(BaseModel):
    proactivity: Proactivity


class FeedbackRequest(BaseModel):
    feedback: Literal["helpful", "not_relevant"]


class DecisionRequest(BaseModel):
    decision: Literal["approve", "dismiss"]
