"use client";

import clsx from "clsx";
import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { MomentChip, StressMeter } from "@/components/advisor";
import { Skeleton } from "@/components/motion";
import { ErrorNote, errorMessage } from "@/components/shell";
import { listCustomers } from "@/lib/api";
import { MOMENT_KEYS, MOMENTS, monthLong } from "@/lib/format";
import type { CustomerSummary, MomentKey } from "@/lib/types";

export default function CustomersPage() {
  const [moment, setMoment] = useState<MomentKey | "">("");
  const [needsReview, setNeedsReview] = useState(false);
  const [rows, setRows] = useState<CustomerSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    listCustomers({ moment, needsReview })
      .then((d) => {
        setError(null);
        setRows(d);
      })
      .catch((err) => setError(errorMessage(err)));
  }, [moment, needsReview]);

  useEffect(load, [load]);

  const reviewTotal = rows?.reduce((sum, r) => sum + r.review_count, 0) ?? 0;

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-navy-900">Customers</h1>
          <p className="mt-1 text-sm text-muted">
            {rows ? `${rows.length} shown` : "Loading"}
            {reviewTotal > 0 && `, ${reviewTotal} ${reviewTotal === 1 ? "action waits" : "actions wait"} for your review`}
          </p>
        </div>
        <button
          type="button"
          aria-pressed={needsReview}
          onClick={() => setNeedsReview((v) => !v)}
          className={clsx(
            "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition",
            needsReview ? "border-amber bg-amber-soft text-amber" : "border-line bg-white text-navy-900 hover:border-navy-500",
          )}
        >
          <span className={clsx("size-2 rounded-full", needsReview ? "bg-amber" : "bg-line")} />
          Needs review
        </button>
      </div>

      <div className="scrollbar-none -mx-4 mt-5 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0" role="group" aria-label="Filter by moment">
        {(["", ...MOMENT_KEYS] as const).map((key) => (
          <button
            key={key || "all"}
            type="button"
            aria-pressed={moment === key}
            onClick={() => setMoment(key)}
            className={clsx(
              "shrink-0 rounded-full px-3.5 py-1.5 text-sm transition",
              moment === key ? "bg-navy-900 font-medium text-white" : "bg-white text-muted ring-1 ring-line hover:text-navy-900",
            )}
          >
            {key ? MOMENTS[key].label : "All moments"}
          </button>
        ))}
      </div>

      <div className="mt-5">
        {error && <ErrorNote message={error} onRetry={load} />}
        {!rows && !error && (
          <ul aria-busy="true" aria-label="Loading customers" className="flex flex-col gap-2">
            {Array.from({ length: 6 }, (_, i) => (
              <li key={i} className="flex items-center gap-4 rounded-2xl border border-line bg-white p-4">
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-40" />
                  <Skeleton className="h-3 w-24" />
                </div>
                <Skeleton className="h-6 w-28 rounded-full" />
                <Skeleton className="hidden h-3 w-20 md:block" />
              </li>
            ))}
          </ul>
        )}
        {rows && rows.length === 0 && (
          <p className="rounded-[var(--radius-card)] border border-dashed border-line bg-white px-4 py-10 text-center text-sm text-muted">
            No customers match these filters. Clear a filter to see more.
          </p>
        )}
        {rows && rows.length > 0 && (
          <>
            {/* Phones: one card per customer. */}
            <ul className="flex flex-col gap-2 md:hidden">
              {rows.map((c) => (
                <li key={c.id}>
                  <Link
                    href={`/advisor/customers/${c.id}`}
                    className="press flex items-center gap-3 rounded-2xl border border-line bg-white p-4 hover:border-navy-500/40 active:bg-paper"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="truncate font-semibold text-navy-900">{c.name}</span>
                        {c.review_count > 0 && (
                          <span className="rounded-full bg-amber-soft px-2 py-0.5 text-xs font-semibold text-amber">
                            {c.review_count} to review
                          </span>
                        )}
                      </div>
                      <p className="mt-0.5 text-sm text-muted">
                        {c.age}, {c.city}
                        {c.next_pinch_month && <span className="text-coral"> · tight in {monthLong(c.next_pinch_month)}</span>}
                      </p>
                      <div className="mt-2.5 flex items-center justify-between gap-2">
                        <MomentChip moment={c.moment_key} confidence={c.moment_confidence} />
                        <StressMeter value={c.stress} />
                      </div>
                    </div>
                    <ChevronRight className="size-5 shrink-0 text-muted" aria-hidden />
                  </Link>
                </li>
              ))}
            </ul>

            {/* Wider screens: a scannable table. */}
            <div className="hidden overflow-hidden rounded-[var(--radius-card)] border border-line bg-white md:block">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-line bg-paper text-xs text-muted">
                  <tr>
                    <th className="px-5 py-3 font-medium">Customer</th>
                    <th className="px-3 py-3 font-medium">Moment</th>
                    <th className="px-3 py-3 font-medium">Stress</th>
                    <th className="px-3 py-3 font-medium">Next pinch</th>
                    <th className="px-5 py-3 text-right font-medium">Review</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((c) => (
                    <tr key={c.id} className="group relative cursor-pointer border-b border-line transition-colors last:border-0 hover:bg-ice/60">
                      <td className="px-5 py-3.5">
                        <Link
                          href={`/advisor/customers/${c.id}`}
                          className="font-semibold text-navy-900 underline-offset-4 after:absolute after:inset-0 group-hover:underline"
                        >
                          {c.name}
                        </Link>
                        <div className="text-xs text-muted">
                          {c.age}, {c.city}
                        </div>
                      </td>
                      <td className="px-3 py-3.5">
                        <MomentChip moment={c.moment_key} confidence={c.moment_confidence} />
                      </td>
                      <td className="px-3 py-3.5">
                        <StressMeter value={c.stress} />
                      </td>
                      <td className="px-3 py-3.5">
                        {c.next_pinch_month ? (
                          <span className="font-medium text-coral">{monthLong(c.next_pinch_month)}</span>
                        ) : (
                          <span className="text-muted">None</span>
                        )}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        {c.review_count > 0 ? (
                          <span className="tabular rounded-full bg-amber-soft px-2.5 py-1 text-xs font-semibold text-amber">
                            {c.review_count}
                          </span>
                        ) : (
                          <span className="text-muted">0</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
