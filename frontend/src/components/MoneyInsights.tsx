"use client";

import clsx from "clsx";
import { Repeat, TrendingUp } from "lucide-react";
import { money, moneyCents } from "@/lib/format";
import type { CategorySpend, Subscription } from "@/lib/types";

/** Where the money goes: average monthly spend per category, from the categorised transactions. */
export function SpendingBreakdown({
  spending,
  limit = 6,
  tone = "light",
  compact = false,
}: {
  spending: CategorySpend[];
  limit?: number;
  tone?: "light" | "card";
  /** Narrow columns (the advisor sidebar): smaller heading, the note under it, no inner card. */
  compact?: boolean;
}) {
  if (spending.length === 0) return null;
  const rows = spending.slice(0, limit);
  const top = rows[0]?.monthly_average || 1;
  return (
    <section aria-labelledby="spending" className={clsx(tone === "card" && "rounded-[var(--radius-card)] border border-line bg-white p-4")}>
      <SectionHead id="spending" title="Where your money goes" meta="per month, last 3 months" compact={compact} />
      <ul className={clsx("mt-3 space-y-3", compact ? "px-0" : "rounded-[var(--radius-card)] bg-white p-4")}>
        {rows.map((r) => (
          <li key={r.category}>
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 font-medium text-navy-900">
                {r.label}
                {r.recurring_share >= 0.6 && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-ice px-2 py-0.5 text-xs font-medium text-navy-700">
                    <Repeat className="size-3" aria-hidden /> recurring
                  </span>
                )}
              </span>
              <span className="tabular shrink-0 whitespace-nowrap text-ink/80">
                {money(r.monthly_average)} <span className="text-muted">· {Math.round(r.share * 100)}%</span>
              </span>
            </div>
            <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-paper" aria-hidden>
              <div className="h-full rounded-full bg-cyan-500" style={{ width: `${Math.max(4, (r.monthly_average / top) * 100)}%` }} />
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-2 px-1 text-xs text-muted">Large one-off payments, like a notary deposit, aren’t counted as monthly spending.</p>
    </section>
  );
}

/** Subscriptions detected from repeating fixed charges, with price rises called out. */
export function SubscriptionList({ subscriptions, compact = false }: { subscriptions: Subscription[]; compact?: boolean }) {
  if (subscriptions.length === 0) return null;
  const total = subscriptions.reduce((sum, s) => sum + s.monthly_amount, 0);
  return (
    <section aria-labelledby="subscriptions">
      <SectionHead
        id="subscriptions"
        title={compact ? "Subscriptions" : "Your subscriptions"}
        meta={`${moneyCents(total)} a month, ${money(total * 12)} a year`}
        compact={compact}
      />
      <ul className={clsx("mt-3 overflow-hidden", compact ? "-mx-1" : "rounded-[var(--radius-card)] bg-white")}>
        {subscriptions.map((s) => (
          <li
            key={s.name}
            className={clsx("flex items-center justify-between gap-3 border-b border-line py-3 last:border-0", compact ? "px-1" : "px-4")}
          >
            <div className="min-w-0">
              <p className="truncate font-medium text-navy-900">{s.name}</p>
              <p className="text-xs text-muted">since {s.since}</p>
            </div>
            <div className="text-right">
              <p className="tabular font-semibold text-navy-900">{moneyCents(s.monthly_amount)}</p>
              {s.price_change && s.price_change.after > s.price_change.before && (
                <p className="inline-flex items-center gap-1 text-xs font-medium text-coral">
                  <TrendingUp className="size-3" aria-hidden />
                  up from {moneyCents(s.price_change.before)}
                </p>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Section heading. Wide: title and note on one line. Compact: the note wraps under the title. */
function SectionHead({ id, title, meta, compact }: { id: string; title: string; meta: string; compact: boolean }) {
  if (compact) {
    return (
      <div className="px-1">
        <h3 id={id} className="font-display text-base font-semibold tracking-tight text-navy-900">
          {title}
        </h3>
        <p className="tabular mt-0.5 text-[13px] text-muted">{meta}</p>
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 px-1">
      <h2 id={id} className="font-display whitespace-nowrap text-xl font-semibold tracking-tight text-navy-900">
        {title}
      </h2>
      <span className="tabular whitespace-nowrap text-sm text-muted">{meta}</span>
    </div>
  );
}
