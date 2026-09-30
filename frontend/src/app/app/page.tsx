"use client";

import clsx from "clsx";
import { Check, ChevronDown, ThumbsDown, ThumbsUp } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useState } from "react";
import { TwinChart } from "@/components/TwinChart";
import { Money, Skeleton, StreamText } from "@/components/motion";
import { BrandMark, ErrorNote, errorMessage, LogoutButton, MockBadge, useSession } from "@/components/shell";
import { getOverview, rejectMoment, sendFeedback, setProactivity } from "@/lib/api";
import {
  dayMonth,
  LINE_LABEL,
  money,
  MOMENTS,
  monthLong,
  PROACTIVITY,
  signedMoney,
} from "@/lib/format";
import type { CustomerOverview, Intervention, Proactivity, TwinMonth } from "@/lib/types";

export default function CustomerApp() {
  const me = useSession("customer");
  const [data, setData] = useState<CustomerOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    getOverview()
      .then((d) => {
        setError(null);
        setData(d);
      })
      .catch((err) => setError(errorMessage(err)));
  }, []);

  useEffect(() => {
    if (me) load();
  }, [me, load]);

  return (
    <main className="flex flex-1 justify-center bg-[#dfe8f1]">
      <div className="relative flex min-h-svh w-full max-w-[420px] flex-col bg-paper sm:my-6 sm:min-h-0 sm:overflow-hidden sm:rounded-[2.25rem] sm:shadow-[0_30px_80px_-30px_rgba(6,34,74,0.45)]">
        {!data && !error && <OverviewSkeleton />}
        {error && (
          <div className="p-5">
            <ErrorNote message={error} onRetry={load} />
          </div>
        )}
        {data && <Overview data={data} onChange={setData} />}
      </div>
    </main>
  );
}

function Overview({ data, onChange }: { data: CustomerOverview; onChange: (d: CustomerOverview) => void }) {
  const { customer, moment, twin, interventions } = data;
  const pinch = twin.pinch_points[0];
  const showMoment = moment && moment.key !== "no_clear_moment" && moment.confidence >= 0.5;

  return (
    <>
      <header className="bg-navy-900 px-5 pb-12 pt-[max(1.25rem,env(safe-area-inset-top))] text-white">
        <div className="flex items-center justify-between">
          <BrandMark />
          <div className="flex items-center gap-1">
            <MockBadge />
            <LogoutButton className="text-ice/80 hover:bg-white/10 hover:text-white" />
          </div>
        </div>
        <p className="mt-7 text-[15px] text-ice/70">Hi {customer.first_name}, your balance today</p>
        <p className="font-display mt-1 text-[2.75rem] font-semibold leading-none tracking-tight">
          <Money value={customer.balance} />
        </p>
        {pinch ? (
          <p className="mt-3 inline-flex items-center gap-2 rounded-full bg-coral/15 px-3 py-1 text-sm text-[#ffb59e]">
            <span className="size-1.5 rounded-full bg-coral" />
            {monthLong(pinch.month).split(" ")[0]} looks tight: {money(pinch.balance)}
          </p>
        ) : (
          <p className="mt-3 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-sm text-ice/80">
            <span className="size-1.5 rounded-full bg-cyan-400" />
            Above your buffer all year
          </p>
        )}
        <h2 className="mt-8 text-sm font-medium text-ice/70">Your next 12 months</h2>
        <TwinChart twin={twin} variant="dark" height={190} className="mt-2" />
      </header>

      <div className="-mt-6 flex flex-col gap-8 rounded-t-[1.75rem] bg-paper px-4 pb-[max(2rem,env(safe-area-inset-bottom))] pt-5">
        <AnimatePresence initial={false}>
          {showMoment && (
            <motion.div key="moment" exit={{ opacity: 0, height: 0, marginBottom: -32 }} transition={{ duration: 0.3 }}>
              <MomentBanner overview={data} onChange={onChange} />
            </motion.div>
          )}
        </AnimatePresence>

        <section aria-labelledby="for-you">
          <h2 id="for-you" className="font-display px-1 text-xl font-semibold tracking-tight text-navy-900">
            For you
          </h2>
          <div className="mt-3 flex flex-col gap-3">
            <AnimatePresence initial={false}>
              {interventions.map((i) => (
                <motion.div
                  key={i.id}
                  layout
                  exit={{ opacity: 0, x: -40, height: 0 }}
                  transition={{ duration: 0.28 }}
                >
                  <InterventionCard item={i} onChange={onChange} />
                </motion.div>
              ))}
            </AnimatePresence>
            {interventions.length === 0 && (
              <p className="rounded-[var(--radius-card)] border border-dashed border-line px-4 py-6 text-center text-sm text-muted">
                Nothing needs your attention. We’ll let you know when something comes up.
              </p>
            )}
          </div>
        </section>

        <UpcomingEvents months={twin.months.slice(0, 3)} pinchMonths={twin.pinch_points.map((p) => p.month)} />

        <ProactivityControl value={customer.proactivity} onChange={onChange} />

        <p className="px-1 pb-2 text-xs leading-relaxed text-muted">
          Forecasts are estimates based on your recent transactions. Items marked as estimates come from a life moment
          we think you’re in, and you can always tell us we got it wrong.
        </p>
      </div>
    </>
  );
}

function MomentBanner({ overview, onChange }: { overview: CustomerOverview; onChange: (d: CustomerOverview) => void }) {
  const moment = overview.moment!;
  const meta = MOMENTS[moment.key];
  const [busy, setBusy] = useState(false);
  const [imgOk, setImgOk] = useState(true);
  const support = moment.key === "financial_stress";

  return (
    <section
      aria-label="What we noticed"
      className="overflow-hidden rounded-[var(--radius-card)] bg-white shadow-[0_12px_32px_-18px_rgba(6,34,74,0.35)]"
    >
      {imgOk && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={meta.image} alt="" className="aspect-[16/8] w-full object-cover" onError={() => setImgOk(false)} />
      )}
      <div className="p-4">
        <p className="font-display text-lg font-semibold leading-snug tracking-tight text-navy-900">
          <StreamText text={meta.headline} id={moment.analyzed_at} />
        </p>
        <p className="mt-1.5 text-[15px] leading-relaxed text-muted">{meta.body}</p>
        <div className="mt-4 flex items-center justify-between gap-3">
          <span className={clsx("text-xs", support ? "text-mint" : "text-muted")}>
            {support ? "We'll only offer support, never products." : `${Math.round(moment.confidence * 100)}% sure`}
          </span>
          <button
            type="button"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                onChange(await rejectMoment());
              } finally {
                setBusy(false);
              }
            }}
            className="rounded-full border border-line px-4 py-2 text-sm font-medium text-navy-900 transition hover:border-navy-500 disabled:opacity-50"
          >
            {busy ? "Updating…" : "Not right"}
          </button>
        </div>
      </div>
    </section>
  );
}

function InterventionCard({ item, onChange }: { item: Intervention; onChange: (d: CustomerOverview) => void }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<null | "helpful" | "not_relevant">(null);
  const support = item.line === "support";
  const warning = item.key.startsWith("pinch_point");

  async function give(feedback: "helpful" | "not_relevant") {
    setBusy(feedback);
    try {
      onChange(await sendFeedback(item.id, feedback));
    } finally {
      setBusy(null);
    }
  }

  return (
    <article
      className={clsx(
        "rounded-[var(--radius-card)] border bg-white p-4",
        warning ? "border-coral/35" : support ? "border-mint/35" : "border-line",
      )}
    >
      <div className="flex items-center justify-between gap-3 text-xs">
        <span
          className={clsx(
            "rounded-full px-2.5 py-1 font-medium",
            warning
              ? "bg-coral-soft text-coral"
              : support
                ? "bg-mint-soft text-mint"
                : "bg-ice text-navy-700",
          )}
        >
          {warning ? "Heads-up" : LINE_LABEL[item.line]}
        </span>
        <time dateTime={item.deliver_at} className="text-muted">
          {dayMonth(item.deliver_at)}
        </time>
      </div>
      <h3 className="font-display mt-3 text-[17px] font-semibold leading-snug tracking-tight text-navy-900">
        {item.title}
      </h3>
      <p className="mt-1.5 text-[15px] leading-relaxed text-ink/80">{item.message}</p>

      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-navy-700"
      >
        Why am I seeing this?
        <ChevronDown className={clsx("size-4 transition-transform", open && "rotate-180")} aria-hidden />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="overflow-hidden"
          >
            <ul className="mt-2 space-y-2 rounded-xl bg-paper p-3">
              {item.reasons.map((r) => (
                <li key={r} className="flex gap-2 text-sm leading-snug text-ink/80">
                  <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-cyan-500" />
                  {r}
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="mt-4 flex gap-2 border-t border-line pt-3">
        {item.feedback === "helpful" ? (
          <span className="inline-flex items-center gap-1.5 py-2 text-sm font-medium text-mint">
            <Check className="size-4" aria-hidden /> Marked as helpful
          </span>
        ) : (
          <>
            <button
              type="button"
              disabled={busy !== null}
              onClick={() => give("helpful")}
              className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-full bg-ice px-3 py-2 text-sm font-medium text-navy-900 transition hover:bg-cyan-300/40 disabled:opacity-50"
            >
              <ThumbsUp className="size-4" aria-hidden /> Helpful
            </button>
            <button
              type="button"
              disabled={busy !== null}
              onClick={() => give("not_relevant")}
              className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-full px-3 py-2 text-sm font-medium text-muted transition hover:bg-paper disabled:opacity-50"
            >
              <ThumbsDown className="size-4" aria-hidden /> Not relevant
            </button>
          </>
        )}
      </div>
    </article>
  );
}

function UpcomingEvents({ months, pinchMonths }: { months: TwinMonth[]; pinchMonths: string[] }) {
  return (
    <section aria-labelledby="coming-up">
      <h2 id="coming-up" className="font-display px-1 text-xl font-semibold tracking-tight text-navy-900">
        Coming up
      </h2>
      <ol className="relative mt-3 rounded-[var(--radius-card)] bg-white px-4 py-1">
        {months.map((m, idx) => {
          const special = m.events.filter((e) => e.source !== "recurring");
          const usual = m.events.filter((e) => e.source === "recurring");
          const usualNet = usual.reduce((sum, e) => sum + e.amount, 0);
          const tight = pinchMonths.includes(m.month);
          return (
            <li key={m.month} className={clsx("relative py-4 pl-6", idx > 0 && "border-t border-line")}>
              <span
                aria-hidden
                className={clsx(
                  "absolute left-0 top-[1.4rem] size-2.5 rounded-full ring-4",
                  tight ? "bg-coral ring-coral-soft" : "bg-navy-500 ring-ice",
                )}
              />
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-semibold text-navy-900">{monthLong(m.month)}</span>
                <span className={clsx("tabular text-sm", tight ? "font-semibold text-coral" : "text-muted")}>
                  ends at {money(m.balance)}
                </span>
              </div>
              <ul className="mt-2 space-y-1.5 text-[15px]">
                {special.map((e) => (
                  <li key={e.label} className="flex items-center justify-between gap-3">
                    <span className="flex min-w-0 items-center gap-2">
                      {e.source === "moment" ? (
                        <span className="shrink-0 rounded-md border border-dashed border-cyan-500 px-1.5 text-[11px] font-medium text-navy-700">
                          Estimate
                        </span>
                      ) : (
                        <span className="shrink-0 rounded-md bg-ice px-1.5 text-[11px] font-medium text-navy-700">Planned</span>
                      )}
                      <span className="truncate">{e.label.replace(/ \(estimate\)$/, "")}</span>
                    </span>
                    <span className={clsx("tabular shrink-0", e.amount > 0 && "text-mint")}>{signedMoney(e.amount)}</span>
                  </li>
                ))}
                <li className="flex items-center justify-between gap-3 text-sm text-muted">
                  <span>Usual income and bills ({usual.length})</span>
                  <span className="tabular">{signedMoney(usualNet)}</span>
                </li>
              </ul>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function OverviewSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading your overview">
      <div className="bg-navy-900 px-5 pb-12 pt-[max(1.25rem,env(safe-area-inset-top))]">
        <BrandMark />
        <Skeleton className="skeleton-dark mt-7 h-4 w-44" />
        <Skeleton className="skeleton-dark mt-3 h-11 w-40" />
        <Skeleton className="skeleton-dark mt-4 h-7 w-52 rounded-full" />
        <Skeleton className="skeleton-dark mt-9 h-[190px] w-full rounded-2xl" />
      </div>
      <div className="-mt-6 space-y-4 rounded-t-[1.75rem] bg-paper px-4 pt-5">
        <Skeleton className="h-60 w-full rounded-[var(--radius-card)]" />
        <Skeleton className="h-6 w-28" />
        <Skeleton className="h-44 w-full rounded-[var(--radius-card)]" />
      </div>
    </div>
  );
}

function ProactivityControl({ value, onChange }: { value: Proactivity; onChange: (d: CustomerOverview) => void }) {
  const [pending, setPending] = useState<Proactivity | null>(null);
  const current = pending ?? value;
  return (
    <section aria-labelledby="proactivity">
      <h2 id="proactivity" className="font-display px-1 text-xl font-semibold tracking-tight text-navy-900">
        How much should we speak up?
      </h2>
      <div role="radiogroup" aria-labelledby="proactivity" className="mt-3 grid grid-cols-3 gap-1 rounded-2xl bg-[#e5edf5] p-1">
        {(Object.keys(PROACTIVITY) as Proactivity[]).map((p) => (
          <button
            key={p}
            type="button"
            role="radio"
            aria-checked={current === p}
            disabled={pending !== null}
            onClick={async () => {
              if (p === value) return;
              setPending(p);
              try {
                onChange(await setProactivity(p));
              } finally {
                setPending(null);
              }
            }}
            className={clsx(
              "relative rounded-xl px-2 py-2.5 text-sm font-medium transition-colors",
              current === p ? "text-navy-900" : "text-muted hover:text-navy-900",
            )}
          >
            {current === p && (
              <motion.span
                layoutId="proactivity-pill"
                className="absolute inset-0 rounded-xl bg-white shadow-sm"
                transition={{ type: "spring", stiffness: 420, damping: 34 }}
              />
            )}
            <span className="relative">{PROACTIVITY[p].label}</span>
          </button>
        ))}
      </div>
      <p className="mt-2 px-1 text-sm text-muted">{PROACTIVITY[current].hint}.</p>
    </section>
  );
}
