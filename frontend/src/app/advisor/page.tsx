"use client";

import clsx from "clsx";
import { ArrowDown, ArrowUp, ChevronRight, Search, X } from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/Button";
import { MomentChip, StressMeter } from "@/components/advisor";
import { CustomerListSkeleton, CustomerRowsSkeleton } from "@/components/skeletons";
import { ErrorNote, errorMessage } from "@/components/shell";
import { listCustomers } from "@/lib/api";
import { MOMENT_KEYS, MOMENTS, monthLong } from "@/lib/format";
import type { CustomerSummary, MomentKey } from "@/lib/types";

type SortKey = "attention" | "name" | "moment" | "stress" | "pinch" | "review";
type Dir = "asc" | "desc";
const PAGE = 40;

const SORTS: Record<SortKey, (a: CustomerSummary, b: CustomerSummary) => number> = {
  // Default: whoever needs a person first — review items, then stress, then the soonest tight month.
  attention: (a, b) =>
    b.review_count - a.review_count ||
    (b.stress ?? 0) - (a.stress ?? 0) ||
    (a.next_pinch_month ?? "9999").localeCompare(b.next_pinch_month ?? "9999"),
  name: (a, b) => a.name.localeCompare(b.name),
  moment: (a, b) => (a.moment_confidence ?? 0) - (b.moment_confidence ?? 0),
  stress: (a, b) => (a.stress ?? 0) - (b.stress ?? 0),
  pinch: (a, b) => (a.next_pinch_month ?? "9999").localeCompare(b.next_pinch_month ?? "9999"),
  review: (a, b) => a.review_count - b.review_count,
};
const DEFAULT_DIR: Record<SortKey, Dir> = { attention: "asc", name: "asc", moment: "desc", stress: "desc", pinch: "asc", review: "desc" };

export default function CustomersPage() {
  return (
    <Suspense fallback={<CustomerListSkeleton />}>
      <Customers />
    </Suspense>
  );
}

function Customers() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  // Filters, search and sort live in the URL, so Back from a customer returns to the same view.
  const moment = (params.get("moment") ?? "") as MomentKey | "";
  const needsReview = params.get("review") === "1";
  const sort = (params.get("sort") ?? "attention") as SortKey;
  const dir = (params.get("dir") ?? DEFAULT_DIR[sort]) as Dir;
  const [query, setQuery] = useState(params.get("q") ?? "");
  const [limit, setLimit] = useState(PAGE);

  const [rows, setRows] = useState<CustomerSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const setParams = useCallback(
    (next: Record<string, string | null>) => {
      // Start from the live URL, not a render-time copy, so a delayed search update can't undo a sort.
      const p = new URLSearchParams(window.location.search);
      for (const [k, v] of Object.entries(next)) {
        if (v == null || v === "") p.delete(k);
        else p.set(k, v);
      }
      const qs = p.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router],
  );

  // One fetch for everyone; filtering, search and sorting are instant on the client.
  const load = useCallback(() => {
    listCustomers()
      .then((d) => {
        setError(null);
        setRows(d);
      })
      .catch((err) => setError(errorMessage(err)));
  }, []);
  useEffect(load, [load]);

  // Keep the search box in the URL without a navigation on every keystroke.
  useEffect(() => {
    const t = window.setTimeout(() => {
      if ((params.get("q") ?? "") !== query) setParams({ q: query || null });
    }, 250);
    return () => window.clearTimeout(t);
  }, [query, params, setParams]);

  const counts = useMemo(() => {
    const c = Object.fromEntries(MOMENT_KEYS.map((k) => [k, 0])) as Record<MomentKey, number>;
    for (const r of rows ?? []) if (r.moment_key) c[r.moment_key] += 1;
    return c;
  }, [rows]);

  const filtered = useMemo(() => {
    if (!rows) return null;
    const q = query.trim().toLowerCase();
    const out = rows.filter(
      (r) =>
        (!moment || r.moment_key === moment) &&
        (!needsReview || r.review_count > 0) &&
        (!q || r.name.toLowerCase().includes(q) || r.city.toLowerCase().includes(q)),
    );
    const cmp = SORTS[sort] ?? SORTS.attention;
    out.sort((a, b) => (dir === "desc" ? -cmp(a, b) : cmp(a, b)) || a.name.localeCompare(b.name));
    return out;
  }, [rows, moment, needsReview, query, sort, dir]);

  const reviewTotal = rows?.reduce((sum, r) => sum + r.review_count, 0) ?? 0;
  const hasFilters = !!moment || needsReview || !!query.trim();
  const visible = filtered?.slice(0, limit) ?? [];

  const toggleSort = (key: SortKey) => {
    const nextDir: Dir = sort === key ? (dir === "asc" ? "desc" : "asc") : DEFAULT_DIR[key];
    setParams({ sort: key === "attention" ? null : key, dir: key === "attention" && nextDir === "asc" ? null : nextDir });
  };

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-navy-900">Customers</h1>
          <p className="mt-1 text-sm text-muted">
            {filtered ? `${filtered.length} of ${rows!.length}` : "Loading"}
            {reviewTotal > 0 && (
              <>
                {", "}
                <button
                  type="button"
                  onClick={() => setParams({ review: needsReview ? null : "1" })}
                  className="font-medium text-amber underline-offset-4 hover:underline"
                >
                  {reviewTotal} {reviewTotal === 1 ? "action waits" : "actions wait"} for your review
                </button>
              </>
            )}
          </p>
        </div>
        <div className="flex w-full items-center gap-2 sm:w-auto">
          <label className="relative flex-1 sm:w-72 sm:flex-none">
            <span className="sr-only">Search by name or city</span>
            <Search aria-hidden className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted" />
            <input
              type="search"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setLimit(PAGE);
              }}
              placeholder="Search name or city"
              className="min-h-11 w-full rounded-xl border border-line bg-white pl-10 pr-9 text-[15px] outline-none transition focus:border-cyan-500 focus:shadow-[0_0_0_4px_rgb(31_182_232/0.15)] sm:min-h-10"
            />
            {query && (
              <button
                type="button"
                onClick={() => setQuery("")}
                aria-label="Clear search"
                className="absolute right-1.5 top-1/2 grid size-8 -translate-y-1/2 place-items-center rounded-lg text-muted hover:bg-paper hover:text-navy-900"
              >
                <X className="size-4" />
              </button>
            )}
          </label>
          <button
            type="button"
            aria-pressed={needsReview}
            onClick={() => setParams({ review: needsReview ? null : "1" })}
            className={clsx(
              "inline-flex min-h-11 shrink-0 items-center gap-2 rounded-xl border px-4 text-sm font-semibold shadow-[0_1px_2px_rgb(4_24_51/0.06)] transition sm:min-h-10",
              needsReview
                ? "border-amber/60 bg-amber-soft text-amber"
                : "border-line bg-white text-navy-900 hover:border-navy-500/45 hover:bg-paper",
            )}
          >
            <span className={clsx("size-2 rounded-full transition-colors", needsReview ? "bg-amber" : "bg-line")} />
            Needs review
          </button>
        </div>
      </div>

      <div
        className="scrollbar-none -mx-4 mt-4 flex gap-2 overflow-x-auto px-4 py-1.5 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0"
        role="group"
        aria-label="Filter by moment"
      >
        {(["", ...MOMENT_KEYS] as const).map((key) => {
          const active = moment === key;
          const n = key ? counts[key] : rows?.length;
          return (
            <button
              key={key || "all"}
              type="button"
              aria-pressed={active}
              onClick={() => {
                setParams({ moment: key || null });
                setLimit(PAGE);
              }}
              className={clsx(
                "relative min-h-10 shrink-0 rounded-full px-4 text-sm font-medium transition-colors",
                active ? "text-white" : "bg-white text-muted ring-1 ring-line hover:bg-paper hover:text-navy-900",
              )}
            >
              {active && (
                <motion.span
                  layoutId="moment-filter-pill"
                  className="absolute inset-0 rounded-full bg-navy-900 shadow-[0_4px_12px_-4px_rgb(6_34_74/0.5)]"
                  transition={{ type: "spring", stiffness: 480, damping: 38 }}
                />
              )}
              <span className="relative inline-flex items-center gap-1.5">
                {key ? MOMENTS[key].label : "All moments"}
                {n != null && <span className={clsx("tabular text-xs", active ? "text-ice/70" : "text-muted/80")}>{n}</span>}
              </span>
            </button>
          );
        })}
      </div>

      <div className="mt-5">
        {error && <ErrorNote message={error} onRetry={load} />}
        {!filtered && !error && <CustomerRowsSkeleton />}
        {filtered && filtered.length === 0 && (
          <div className="rounded-[var(--radius-card)] border border-dashed border-line bg-white px-4 py-10 text-center">
            <p className="font-semibold text-navy-900">No customers match{query.trim() ? ` “${query.trim()}”` : " these filters"}.</p>
            <p className="mt-1 text-sm text-muted">Try a first name or a city, or clear the filters to see everyone.</p>
            {hasFilters && (
              <Button
                variant="secondary"
                size="sm"
                className="mt-4"
                onClick={() => {
                  setQuery("");
                  setParams({ moment: null, review: null, q: null });
                }}
              >
                Clear filters
              </Button>
            )}
          </div>
        )}

        {filtered && filtered.length > 0 && (
          <>
            {/* Phones: one card per customer. */}
            <ul className="flex flex-col gap-2 md:hidden">
              {visible.map((c, i) => (
                <li key={c.id} className="row-in" style={{ animationDelay: `${Math.min(i, 10) * 30}ms` }}>
                  <Link
                    href={`/advisor/customers/${c.id}`}
                    className="press elev-1 flex items-center gap-3 rounded-2xl bg-white p-4 active:bg-paper"
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

            {/* Wider screens: a scannable, sortable table. */}
            <div className="elev-1 hidden rounded-[var(--radius-card)] bg-white md:block">
              <table className="w-full text-left text-sm">
                <thead className="sticky top-[6.5rem] z-10 bg-paper/95 text-xs text-muted backdrop-blur">
                  <tr className="border-b border-line">
                    <SortHead label="Customer" k="name" sort={sort} dir={dir} onSort={toggleSort} className="rounded-tl-[var(--radius-card)] pl-5" />
                    <SortHead label="Moment" k="moment" sort={sort} dir={dir} onSort={toggleSort} />
                    <SortHead label="Stress" k="stress" sort={sort} dir={dir} onSort={toggleSort} />
                    <SortHead label="Next pinch" k="pinch" sort={sort} dir={dir} onSort={toggleSort} />
                    <SortHead label="Review" k="review" sort={sort} dir={dir} onSort={toggleSort} align="right" className="rounded-tr-[var(--radius-card)] pr-5" />
                  </tr>
                </thead>
                <tbody>
                  {visible.map((c, i) => (
                    <tr
                      key={c.id}
                      className="row-in group relative cursor-pointer border-b border-line transition-colors last:border-0 hover:bg-ice/60"
                      style={{ animationDelay: `${Math.min(i, 12) * 22}ms` }}
                    >
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

            {filtered.length > limit && (
              <div className="mt-4 flex justify-center">
                <Button variant="secondary" onClick={() => setLimit((l) => l + PAGE)}>
                  Show {Math.min(PAGE, filtered.length - limit)} more of {filtered.length - limit}
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function SortHead({
  label,
  k,
  sort,
  dir,
  onSort,
  align = "left",
  className,
}: {
  label: string;
  k: SortKey;
  sort: SortKey;
  dir: Dir;
  onSort: (k: SortKey) => void;
  align?: "left" | "right";
  className?: string;
}) {
  const active = sort === k;
  return (
    <th
      scope="col"
      aria-sort={active ? (dir === "asc" ? "ascending" : "descending") : "none"}
      className={clsx("px-3 py-2 font-medium", align === "right" && "text-right", className)}
    >
      <button
        type="button"
        onClick={() => onSort(k)}
        className={clsx(
          "-mx-2 inline-flex min-h-8 items-center gap-1 rounded-lg px-2 transition-colors hover:bg-white hover:text-navy-900",
          active && "text-navy-900",
        )}
      >
        {label}
        <span className={clsx("transition-opacity", active ? "opacity-100" : "opacity-0 group-hover:opacity-40")}>
          {active && dir === "asc" ? <ArrowUp className="size-3.5" /> : <ArrowDown className="size-3.5" />}
        </span>
      </button>
    </th>
  );
}
