// Shared API contract (see openspec/changes/kbc-foresight/design.md "Types").
// Frozen: change only with agreement from both workstreams, together with the
// backend Pydantic schemas and the fixtures in src/mocks/.

export type Role = "customer" | "advisor";
export type MomentKey =
  | "moving_home"
  | "growing_family"
  | "new_job"
  | "approaching_retirement"
  | "buying_car"
  | "travel_abroad"
  | "financial_stress"
  | "no_clear_moment";
export type Proactivity = "minimal" | "balanced" | "proactive";
export type TransactionCategory =
  | "income"
  | "housing"
  | "energy"
  | "telecom"
  | "groceries"
  | "transport"
  | "subscriptions"
  | "entertainment"
  | "dining"
  | "shopping"
  | "health"
  | "insurance"
  | "travel"
  | "family"
  | "loans"
  | "fees"
  | "savings"
  | "other";

export interface Me {
  role: Role;
  display_name: string;
}

export interface CustomerProfile {
  id: number;
  first_name: string;
  last_name: string;
  age: number;
  city: string;
  marketing_consent: boolean;
  proactivity: Proactivity;
  balance: number;
}

export interface Signal {
  id: number;
  date: string; // YYYY-MM-DD
  description: string;
  amount: number | null;
  kind: "transaction" | "app_event" | "search" | "contact";
  category: TransactionCategory | null; // transactions only
  recurring: boolean; // repeats monthly (or yearly, for periodic payments)
}

export interface Subscription {
  name: string;
  monthly_amount: number;
  yearly_amount: number;
  since: string; // YYYY-MM
  last_charged: string; // YYYY-MM-DD
  price_change: { before: number; after: number } | null;
}

export interface CategorySpend {
  category: TransactionCategory;
  label: string;
  monthly_average: number;
  share: number; // of all spending, 0..1
  recurring_share: number; // part of this category that repeats, 0..1
}

export interface SignalCreate {
  kind: Signal["kind"];
  description: string; // 1..200 chars
  amount?: number | null;
  date?: string;
}

export interface Moment {
  key: MomentKey;
  label: string;
  confidence: number;
  probabilities: Record<MomentKey, number>;
  stress: number;
  receptiveness: 0 | 1 | 2;
  rationale: string;
  source: "jev" | "gemini" | "rules" | "customer";
  analyzed_at: string; // ISO timestamp
}

export interface TwinEvent {
  label: string;
  amount: number;
  kind: "income" | "expense";
  source: "recurring" | "scheduled" | "moment";
}

export interface TwinMonth {
  month: string; // YYYY-MM
  income: number;
  expenses: number;
  balance: number;
  events: TwinEvent[];
}

export interface PinchPoint {
  month: string;
  balance: number;
  reason: string;
}

export interface Twin {
  start_balance: number;
  months: TwinMonth[];
  pinch_points: PinchPoint[];
}

export interface Intervention {
  id: number;
  key: string;
  title: string;
  message: string;
  line: "banking" | "insurance" | "investing" | "support";
  channel: "app" | "email" | "advisor";
  status: "delivered" | "review" | "held" | "dismissed";
  deliver_at: string; // YYYY-MM-DD
  reasons: string[];
  feedback: "helpful" | "not_relevant" | null;
  cta: string | null; // the card's one direct action, e.g. "Get home insurance"
}

export interface CustomerOverview {
  customer: CustomerProfile;
  moment: Moment | null;
  twin: Twin;
  interventions: Intervention[]; // delivered only, not_relevant excluded
  subscriptions: Subscription[];
  spending: CategorySpend[];
}

export interface CustomerSummary {
  id: number;
  name: string;
  age: number;
  city: string;
  moment_key: MomentKey | null;
  moment_confidence: number | null;
  stress: number | null;
  next_pinch_month: string | null;
  review_count: number;
}

export interface CustomerDetail {
  customer: CustomerProfile;
  signals: Signal[]; // newest first
  moment: Moment | null;
  twin: Twin;
  interventions: Intervention[]; // all statuses
  subscriptions: Subscription[];
  spending: CategorySpend[];
}

export interface ScaleStats {
  population: number;
  moments: Record<MomentKey, number>;
  interventions: Record<Intervention["status"], number>;
  automation_rate: number; // delivered / (delivered + review)
  avg_tokens_per_analysis: number;
  avg_cost_per_analysis_eur: number;
  assumptions: {
    customers: number;
    daily_reevaluation_rate: number;
    price_per_million_input_tokens_eur: number;
    price_per_million_output_tokens_eur: number;
  };
  projected_daily_cost_eur: number;
  projected_monthly_cost_eur: number;
}
