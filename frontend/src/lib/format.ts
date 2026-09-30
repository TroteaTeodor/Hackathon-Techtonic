import type { Intervention, MomentKey, Proactivity, Signal, TransactionCategory } from "./types";

const eur = new Intl.NumberFormat("en-GB", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const eurCents = new Intl.NumberFormat("en-GB", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export const money = (value: number) => eur.format(value).replace("-", "−");
export const moneyCents = (value: number) => eurCents.format(value).replace("-", "−");
export const signedMoney = (value: number) => (value > 0 ? `+${money(value)}` : money(value));
export const percent = (value: number, digits = 0) => `${(value * 100).toFixed(digits)}%`;
export const count = (value: number) => new Intl.NumberFormat("en-GB").format(value);

function parseMonth(month: string) {
  const [y, m] = month.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, 1));
}

export const monthShort = (month: string) =>
  parseMonth(month).toLocaleDateString("en-GB", { month: "short", timeZone: "UTC" });
export const monthLong = (month: string) =>
  parseMonth(month).toLocaleDateString("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });
export const dayMonth = (date: string) =>
  new Date(`${date}T00:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });

export const initials = (first: string, last: string) => `${first[0] ?? ""}${last[0] ?? ""}`.toUpperCase();

export interface MomentMeta {
  label: string;
  /** How the customer app says it, in second person. */
  headline: string;
  /** One reassuring line under the headline. */
  body: string;
  image: string;
}

export const MOMENTS: Record<MomentKey, MomentMeta> = {
  moving_home: {
    label: "Moving home",
    headline: "Looks like you're moving home",
    body: "We've added the notary fees, the move and a first mortgage payment to your forecast.",
    image: "/moments/moving_home.webp",
  },
  growing_family: {
    label: "Growing family",
    headline: "Looks like your family is growing",
    body: "Childcare, baby gear and child benefit are now part of your forecast.",
    image: "/moments/growing_family.webp",
  },
  new_job: {
    label: "New job",
    headline: "Looks like you've started a new job",
    body: "Your forecast now includes the higher salary from next month.",
    image: "/moments/new_job.webp",
  },
  approaching_retirement: {
    label: "Approaching retirement",
    headline: "Retirement is getting closer",
    body: "We've projected your income after you retire, so there are no surprises.",
    image: "/moments/approaching_retirement.webp",
  },
  buying_car: {
    label: "Buying a car",
    headline: "Looks like you're shopping for a car",
    body: "The deposit and a typical car loan are now in your forecast.",
    image: "/moments/buying_car.webp",
  },
  travel_abroad: {
    label: "Travel abroad",
    headline: "Looks like a trip abroad is coming up",
    body: "We've set aside the trip costs in your forecast.",
    image: "/moments/travel_abroad.webp",
  },
  financial_stress: {
    label: "Money is tight",
    headline: "Things look a bit tight right now",
    body: "You're not alone in this. We'd like to help you get back on track, without selling you anything.",
    image: "/moments/financial_stress.webp",
  },
  no_clear_moment: {
    label: "No clear moment",
    headline: "Nothing unusual on the horizon",
    body: "Your money is following its usual rhythm.",
    image: "/moments/no_clear_moment.webp",
  },
};

export const MOMENT_KEYS = Object.keys(MOMENTS) as MomentKey[];

export const PROACTIVITY: Record<Proactivity, { label: string; hint: string }> = {
  minimal: { label: "Minimal", hint: "Only warnings and support" },
  balanced: { label: "Balanced", hint: "Suggestions when we're confident" },
  proactive: { label: "Proactive", hint: "Tell me about anything useful" },
};

export const CATEGORY_LABEL: Record<TransactionCategory, string> = {
  income: "Income", housing: "Housing", energy: "Energy & water", telecom: "Phone & internet",
  groceries: "Groceries", transport: "Transport", subscriptions: "Subscription", entertainment: "Entertainment",
  dining: "Eating out", shopping: "Shopping", health: "Health", insurance: "Insurance", travel: "Travel",
  family: "Family & children", loans: "Loans & credit", fees: "Bank fees & interest", savings: "Savings", other: "Other",
};

export const LINE_LABEL: Record<Intervention["line"], string> = {
  banking: "Banking",
  insurance: "Insurance",
  investing: "Investing",
  support: "Support",
};

export const STATUS_LABEL: Record<Intervention["status"], string> = {
  delivered: "Delivered",
  review: "Needs review",
  held: "Held",
  dismissed: "Dismissed",
};

export const CHANNEL_LABEL: Record<Intervention["channel"], string> = {
  app: "In app",
  email: "Email",
  advisor: "Advisor call",
};

export const SIGNAL_KIND_LABEL: Record<Signal["kind"], string> = {
  transaction: "Transaction",
  app_event: "App activity",
  search: "Search",
  contact: "Contact",
};

export const RECEPTIVENESS_LABEL = ["Not now", "Open", "Receptive"] as const;
