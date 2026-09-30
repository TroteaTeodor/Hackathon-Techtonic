"use client";

import clsx from "clsx";
import { useCallback, useEffect, useState } from "react";
import { STATUS_TONE } from "@/components/advisor";
import { Num, Skeleton } from "@/components/motion";
import { ErrorNote, errorMessage } from "@/components/shell";
import { getScale } from "@/lib/api";
import { count, money, moneyCents, MOMENT_KEYS, MOMENTS, percent, STATUS_LABEL } from "@/lib/format";
import type { Intervention, ScaleStats } from "@/lib/types";

const EUR2 = { style: "currency", currency: "EUR", minimumFractionDigits: 2, maximumFractionDigits: 2 } as const;
const STATUS_ORDER: Intervention["status"][] = ["delivered", "review", "held", "dismissed"];
const STATUS_BAR: Record<Intervention["status"], string> = {
  delivered: "bg-mint",
  review: "bg-amber",
  held: "bg-navy-500/50",
  dismissed: "bg-line",
};

export default function ScalePage() {
  const [data, setData] = useState<ScaleStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    getScale()
      .then((d) => {
        setError(null);
        setData(d);
      })
      .catch((err) => setError(errorMessage(err)));
  }, []);
  useEffect(load, [load]);

  if (error) return <ErrorNote message={error} onRetry={load} />;
  if (!data)
    return (
      <div aria-busy="true" aria-label="Loading scale view" className="flex flex-col gap-5">
        <Skeleton className="h-80 w-full rounded-[1.75rem]" />
        <Skeleton className="h-72 w-full rounded-[var(--radius-card)]" />
      </div>
    );

  const a = data.assumptions;
  const analysesPerDay = a.customers * a.daily_reevaluation_rate;
  const momentMax = Math.max(...Object.values(data.moments));
  const statusTotal = STATUS_ORDER.reduce((s, k) => s + data.interventions[k], 0) || 1;

  return (
    <div className="flex flex-col gap-5">
      <section className="overflow-hidden rounded-[1.75rem] bg-navy-900 p-5 text-white sm:p-8">
        <h1 className="font-display max-w-2xl text-[1.9rem] font-semibold leading-tight tracking-tight sm:text-4xl">
          All {count(a.customers)} KBC customers, looked after for about{" "}
          {money(data.projected_daily_cost_eur)} a day.
        </h1>
        <div className="mt-7 grid gap-6 sm:grid-cols-2">
          <div>
            <p className="text-sm text-ice/65">Projected AI cost per day</p>
            <p className="font-display tabular mt-1 text-5xl font-semibold tracking-tight text-cyan-300 sm:text-6xl">
              <Num value={data.projected_daily_cost_eur} format={EUR2} />
            </p>
          </div>
          <div>
            <p className="text-sm text-ice/65">Per month</p>
            <p className="font-display tabular mt-1 text-5xl font-semibold tracking-tight sm:text-6xl">
              <Num value={data.projected_monthly_cost_eur} format={EUR2} />
            </p>
          </div>
        </div>
        <p className="tabular mt-6 rounded-2xl bg-white/[0.07] px-4 py-3 text-sm leading-relaxed text-ice/85">
          {count(a.customers)} customers × {percent(a.daily_reevaluation_rate)} re-analyzed per day ={" "}
          {count(analysesPerDay)} analyses a day, at €{data.avg_cost_per_analysis_eur.toFixed(6)} each
        </p>
        <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-4">
          <Assumption label="Customers" value={count(a.customers)} />
          <Assumption label="Re-analyzed per day" value={percent(a.daily_reevaluation_rate)} />
          <Assumption label="Input tokens" value={`${moneyCents(a.price_per_million_input_tokens_eur)} per million`} />
          <Assumption label="Output tokens" value={`${moneyCents(a.price_per_million_output_tokens_eur)} per million`} />
        </dl>
      </section>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <section className="rounded-[var(--radius-card)] border border-line bg-white p-5">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="font-display text-lg font-semibold tracking-tight text-navy-900">Moments in the pilot</h2>
            <span className="tabular text-sm text-muted">{count(data.population)} customers</span>
          </div>
          <ul className="mt-4 space-y-2.5">
            {MOMENT_KEYS.map((k) => {
              const n = data.moments[k] ?? 0;
              return (
                <li key={k} className="grid grid-cols-[9.5rem_minmax(0,1fr)_4.5rem] items-center gap-3 text-sm">
                  <span className={clsx("truncate", k === "financial_stress" ? "text-coral" : "text-ink")}>{MOMENTS[k].label}</span>
                  <span className="h-2.5 overflow-hidden rounded-full bg-paper">
                    <span
                      className={clsx(
                        "block h-full rounded-full",
                        k === "financial_stress" ? "bg-coral" : k === "no_clear_moment" ? "bg-navy-500/30" : "bg-cyan-500",
                      )}
                      style={{ width: `${(n / momentMax) * 100}%` }}
                    />
                  </span>
                  <span className="tabular text-right text-muted">
                    {n} <span className="text-xs">({percent(n / data.population)})</span>
                  </span>
                </li>
              );
            })}
          </ul>
        </section>

        <section className="flex flex-col rounded-[var(--radius-card)] border border-line bg-white p-5">
          <h2 className="font-display text-lg font-semibold tracking-tight text-navy-900">Who handles each action</h2>
          <p className="mt-4 font-display tabular text-5xl font-semibold tracking-tight text-navy-900">{percent(data.automation_rate)}</p>
          <p className="mt-1 text-sm text-muted">
            sent automatically. The other {percent(1 - data.automation_rate)} wait for an advisor, because the customer is
            stressed or we aren’t sure enough.
          </p>
          <div className="mt-5 flex h-3 overflow-hidden rounded-full" aria-hidden>
            {STATUS_ORDER.map((s) => (
              <span key={s} className={STATUS_BAR[s]} style={{ width: `${(data.interventions[s] / statusTotal) * 100}%` }} />
            ))}
          </div>
          <ul className="mt-4 grid grid-cols-2 gap-2 text-sm">
            {STATUS_ORDER.map((s) => (
              <li key={s} className="flex items-center justify-between gap-2 rounded-xl bg-paper px-3 py-2">
                <span className={clsx("rounded-full px-2 py-0.5 text-xs font-medium", STATUS_TONE[s])}>{STATUS_LABEL[s]}</span>
                <span className="tabular font-semibold text-navy-900">{data.interventions[s]}</span>
              </li>
            ))}
          </ul>
          <dl className="mt-auto grid grid-cols-2 gap-3 pt-5 text-sm">
            <div>
              <dt className="text-muted">Tokens per analysis</dt>
              <dd className="tabular font-semibold text-navy-900">{count(data.avg_tokens_per_analysis)}</dd>
            </div>
            <div>
              <dt className="text-muted">Cost per analysis</dt>
              <dd className="tabular font-semibold text-navy-900">€{data.avg_cost_per_analysis_eur.toFixed(6)}</dd>
            </div>
          </dl>
        </section>
      </div>

      <p className="text-xs leading-relaxed text-muted">
        The forecast and the guardrails are plain arithmetic and rules, so they cost nothing per customer. Only the moment
        detection calls the AI model, and only when a customer’s signals change.
      </p>
    </div>
  );
}

function Assumption({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-ice/55">{label}</dt>
      <dd className="tabular font-medium text-white">{value}</dd>
    </div>
  );
}
