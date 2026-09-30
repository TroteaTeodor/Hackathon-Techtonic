"use client";

import clsx from "clsx";
import { ArrowLeft, ArrowRight, Baby, Car, FileSignature, Landmark, Sparkles, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { MomentChip, Panel, StatusBadge } from "@/components/advisor";
import { Money, Skeleton, StreamText } from "@/components/motion";
import { ErrorNote, errorMessage, Spinner } from "@/components/shell";
import { TwinChart } from "@/components/TwinChart";
import { decideIntervention, getCustomer, injectSignal } from "@/lib/api";
import {
  CHANNEL_LABEL,
  dayMonth,
  LINE_LABEL,
  money,
  MOMENTS,
  monthLong,
  percent,
  PROACTIVITY,
  RECEPTIVENESS_LABEL,
  SIGNAL_KIND_LABEL,
  signedMoney,
} from "@/lib/format";
import type { CustomerDetail, Intervention, MomentKey, Signal, SignalCreate } from "@/lib/types";

const PRESETS: { label: string; icon: typeof Landmark; signal: SignalCreate }[] = [
  {
    label: "Notary deposit",
    icon: FileSignature,
    signal: { kind: "transaction", description: "Notary deposit — Notaris Peeters", amount: -15000 },
  },
  {
    label: "Baby-store purchase",
    icon: Baby,
    signal: { kind: "transaction", description: "Baby store — Dreambaby Mechelen", amount: -640 },
  },
  {
    label: "Missed loan payment",
    icon: TriangleAlert,
    signal: { kind: "transaction", description: "Missed loan payment — direct debit returned", amount: -420 },
  },
  {
    label: "Car dealer quote",
    icon: Car,
    signal: { kind: "contact", description: "Car dealer quote requested — Toyota Mechelen", amount: null },
  },
];

interface Change {
  moment?: { from: MomentKey | null; to: MomentKey | null; confidence: number | null };
  balance?: { from: number; to: number };
  pinch?: { from: string | null; to: string | null };
  newInterventions: number[];
  newSignal?: number;
}

function diff(before: CustomerDetail, after: CustomerDetail): Change {
  const beforeIds = new Set(before.interventions.map((i) => i.id));
  const beforeSignals = new Set(before.signals.map((s) => s.id));
  const change: Change = {
    newInterventions: after.interventions.filter((i) => !beforeIds.has(i.id)).map((i) => i.id),
    newSignal: after.signals.find((s) => !beforeSignals.has(s.id))?.id,
  };
  if (before.moment?.key !== after.moment?.key)
    change.moment = { from: before.moment?.key ?? null, to: after.moment?.key ?? null, confidence: after.moment?.confidence ?? null };
  if (before.customer.balance !== after.customer.balance)
    change.balance = { from: before.customer.balance, to: after.customer.balance };
  const pb = before.twin.pinch_points[0]?.month ?? null;
  const pa = after.twin.pinch_points[0]?.month ?? null;
  if (pb !== pa) change.pinch = { from: pb, to: pa };
  return change;
}

export default function CustomerDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const [data, setData] = useState<CustomerDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [change, setChange] = useState<Change | null>(null);
  const [flashKey, setFlashKey] = useState(0);
  const topRef = useRef<HTMLDivElement>(null);

  const validId = Number.isInteger(id) && id > 0;

  const load = useCallback(() => {
    if (!validId) return;
    getCustomer(id)
      .then((d) => {
        setError(null);
        setData(d);
      })
      .catch((err) => setError(errorMessage(err)));
  }, [id, validId]);

  useEffect(load, [load]);

  function applyUpdate(next: CustomerDetail) {
    if (data) {
      setChange(diff(data, next));
      setFlashKey((k) => k + 1);
      topRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    setData(next);
  }

  if (!validId)
    return <ErrorNote message="This customer link isn't valid. Go back to the list and pick a customer." />;
  if (error) return <ErrorNote message={error} onRetry={load} />;
  if (!data) return <DetailSkeleton />;

  const { customer, moment, twin, interventions, signals } = data;
  const flash = (on: boolean) => flashKey > 0 && on;

  return (
    <div ref={topRef} className="scroll-mt-28">
      <Link href="/advisor" className="inline-flex items-center gap-1.5 text-sm font-medium text-navy-700 hover:text-navy-900">
        <ArrowLeft className="size-4" aria-hidden /> All customers
      </Link>

      <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight text-navy-900 sm:text-4xl">
            {customer.first_name} {customer.last_name}
          </h1>
          <p className="mt-1 text-muted">
            {customer.age}, {customer.city}
          </p>
        </div>
        <dl className="flex flex-wrap gap-2 text-sm">
          <Fact label="Balance" value={<Money value={customer.balance} />} flash={flash(!!change?.balance)} k={flashKey} />
          <Fact label="Proactivity" value={PROACTIVITY[customer.proactivity].label} />
          <Fact
            label="Marketing"
            value={customer.marketing_consent ? "Consent given" : "No consent"}
            tone={customer.marketing_consent ? undefined : "text-coral"}
          />
        </dl>
      </div>

      {change && (change.moment || change.balance || change.pinch || change.newInterventions.length > 0) && (
          <div
            key={flashKey}
            className="flash-change mt-5 rounded-[var(--radius-card)] bg-navy-900 p-4 text-white sm:p-5"
            role="status"
          >
            <p className="flex items-center gap-2 text-sm font-medium text-cyan-300">
              <Sparkles className="size-4" aria-hidden /> Re-analyzed just now
            </p>
            <ul className="mt-2 grid gap-2 text-[15px] sm:grid-cols-2">
              {change.moment && (
                <li className="flex flex-wrap items-center gap-2">
                  <span className="text-ice/70">Moment</span>
                  <span>{change.moment.from ? MOMENTS[change.moment.from].label : "None"}</span>
                  <ArrowRight className="size-4 text-cyan-400" aria-hidden />
                  <span className="font-semibold">
                    {change.moment.to ? MOMENTS[change.moment.to].label : "None"}
                    {change.moment.confidence != null && ` (${percent(change.moment.confidence)})`}
                  </span>
                </li>
              )}
              {change.balance && (
                <li className="flex flex-wrap items-center gap-2">
                  <span className="text-ice/70">Balance</span>
                  <span className="tabular">{money(change.balance.from)}</span>
                  <ArrowRight className="size-4 text-cyan-400" aria-hidden />
                  <span className="tabular font-semibold">{money(change.balance.to)}</span>
                </li>
              )}
              {change.pinch && (
                <li className="flex flex-wrap items-center gap-2">
                  <span className="text-ice/70">Pinch point</span>
                  <span className="font-semibold">
                    {change.pinch.to ? `Tight in ${monthLong(change.pinch.to)}` : "No longer tight"}
                  </span>
                </li>
              )}
              {change.newInterventions.length > 0 && (
                <li className="flex flex-wrap items-center gap-2">
                  <span className="text-ice/70">Actions</span>
                  <span className="font-semibold">
                    {change.newInterventions.length} new, see below
                  </span>
                </li>
              )}
            </ul>
          </div>
        )}

      <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="flex min-w-0 flex-col gap-5">
          <Panel
            key={`moment-${flashKey}`}
            title="Life moment"
            flash={flash(!!change?.moment)}
            aside={moment && <SourceBadge source={moment.source} />}
          >
            {moment ? <MomentDetail moment={moment} /> : <p className="text-sm text-muted">Not analyzed yet.</p>}
          </Panel>

          <Panel
            key={`twin-${flashKey}`}
            title="Next 12 months"
            flash={flash(!!change?.balance || !!change?.pinch)}
            aside={
              twin.pinch_points[0] ? (
                <span className="text-sm font-medium text-coral">Tight in {monthLong(twin.pinch_points[0].month)}</span>
              ) : (
                <span className="text-sm text-muted">Above buffer all year</span>
              )
            }
          >
            <TwinChart twin={twin} height={240} />
          </Panel>

          <Panel
            key={`int-${flashKey}`}
            title="Actions"
            flash={flash((change?.newInterventions.length ?? 0) > 0)}
            aside={<span className="text-sm text-muted">{interventions.length} total</span>}
          >
            <ul className="flex flex-col gap-3">
              {interventions.map((i) => (
                <InterventionRow
                  key={i.id}
                  item={i}
                  isNew={change?.newInterventions.includes(i.id) ?? false}
                  onDecided={(updated) =>
                    setData((d) =>
                      d ? { ...d, interventions: d.interventions.map((x) => (x.id === updated.id ? updated : x)) } : d,
                    )
                  }
                />
              ))}
              {interventions.length === 0 && <p className="text-sm text-muted">No actions for this customer.</p>}
            </ul>
          </Panel>
        </div>

        <div className="flex min-w-0 flex-col gap-5 lg:sticky lg:top-32 lg:self-start">
          <InjectPanel customerId={customer.id} onUpdated={applyUpdate} />
          <Panel title="Signals" aside={<span className="text-sm text-muted">Newest first</span>}>
            <SignalTimeline signals={signals} highlight={change?.newSignal} />
          </Panel>
        </div>
      </div>
    </div>
  );
}

function Fact({
  label,
  value,
  tone,
  flash,
  k,
}: {
  label: string;
  value: React.ReactNode;
  tone?: string;
  flash?: boolean;
  k?: number;
}) {
  return (
    <div key={flash ? k : undefined} className={clsx("rounded-2xl border border-line bg-white px-3.5 py-2", flash && "flash-change")}>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className={clsx("tabular font-semibold text-navy-900", tone)}>{value}</dd>
    </div>
  );
}

function SourceBadge({ source }: { source: "gemini" | "rules" | "customer" }) {
  const text = { gemini: "Gemini", rules: "Rules fallback", customer: "Set by customer" }[source];
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-ice px-2.5 py-1 text-xs font-medium text-navy-700">
      {source === "gemini" && <Sparkles className="size-3.5" aria-hidden />}
      {text}
    </span>
  );
}

function MomentDetail({ moment }: { moment: NonNullable<CustomerDetail["moment"]> }) {
  const sorted = (Object.entries(moment.probabilities) as [MomentKey, number][]).sort((a, b) => b[1] - a[1]);
  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <MomentChip moment={moment.key} confidence={moment.confidence} />
        <span className="text-xs text-muted">
          Analyzed {new Date(moment.analyzed_at).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}
        </span>
      </div>
      <div className="mt-3 flex items-start gap-4">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          key={moment.key}
          src={MOMENTS[moment.key].image}
          alt=""
          className="hidden aspect-[4/3] w-32 shrink-0 rounded-xl object-cover sm:block"
          onError={(e) => (e.currentTarget.style.visibility = "hidden")}
        />
        <p className="max-w-prose text-[15px] leading-relaxed text-ink/85">
          <StreamText text={moment.rationale} id={moment.analyzed_at} />
        </p>
      </div>

      <div className="mt-4 grid gap-x-8 gap-y-4 sm:grid-cols-[minmax(0,1fr)_180px]">
        <ul className="space-y-2" aria-label="Probability per moment">
          {sorted.map(([key, p]) => (
            <li key={key} className="grid grid-cols-[8.5rem_minmax(0,1fr)_2.75rem] items-center gap-3 text-sm">
              <span className={clsx("truncate", key === moment.key ? "font-semibold text-navy-900" : "text-muted")}>
                {MOMENTS[key].label}
              </span>
              <span className="h-2 overflow-hidden rounded-full bg-paper">
                <span
                  className={clsx(
                    "block h-full rounded-full transition-[width] duration-700 ease-out",
                    key === moment.key ? "bg-cyan-500" : "bg-navy-500/35",
                  )}
                  style={{ width: `${Math.max(p * 100, 1)}%` }}
                />
              </span>
              <span className="tabular text-right text-muted">{percent(p)}</span>
            </li>
          ))}
        </ul>
        <dl className="grid grid-cols-2 gap-3 self-start sm:grid-cols-1">
          <div className="rounded-2xl bg-paper p-3">
            <dt className="text-xs text-muted">Stress</dt>
            <dd className={clsx("tabular font-display text-2xl font-semibold", moment.stress >= 0.6 ? "text-coral" : "text-navy-900")}>
              {percent(moment.stress)}
            </dd>
          </div>
          <div className="rounded-2xl bg-paper p-3">
            <dt className="text-xs text-muted">Receptiveness</dt>
            <dd className="font-display text-2xl font-semibold text-navy-900">{RECEPTIVENESS_LABEL[moment.receptiveness]}</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}

function InterventionRow({
  item,
  isNew,
  onDecided,
}: {
  item: Intervention;
  isNew: boolean;
  onDecided: (i: Intervention) => void;
}) {
  const [busy, setBusy] = useState<null | "approve" | "dismiss">(null);
  const [error, setError] = useState<string | null>(null);

  async function decide(decision: "approve" | "dismiss") {
    setBusy(decision);
    setError(null);
    try {
      onDecided(await decideIntervention(item.id, decision));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <li
      className={clsx(
        "rounded-2xl border p-4",
        item.status === "review" ? "border-amber/40 bg-amber-soft/40" : "border-line",
        isNew && "ring-2 ring-cyan-500/60",
      )}
    >
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <StatusBadge status={item.status} />
        {isNew && <span className="rounded-full bg-cyan-500 px-2 py-0.5 font-semibold text-white">New</span>}
        <span className="text-muted">
          {LINE_LABEL[item.line]}, {CHANNEL_LABEL[item.channel]}, {dayMonth(item.deliver_at)}
        </span>
        {item.feedback && (
          <span className={clsx("ml-auto font-medium", item.feedback === "helpful" ? "text-mint" : "text-muted")}>
            Customer: {item.feedback === "helpful" ? "helpful" : "not relevant"}
          </span>
        )}
      </div>
      <h3 className="mt-2 font-semibold text-navy-900">{item.title}</h3>
      <p className="mt-1 text-sm leading-relaxed text-ink/80">{item.message}</p>
      <ul className="mt-2.5 space-y-1">
        {item.reasons.map((r) => (
          <li key={r} className="flex gap-2 text-[13px] leading-snug text-muted">
            <span className="mt-1.5 size-1 shrink-0 rounded-full bg-muted" />
            {r}
          </li>
        ))}
      </ul>
      {item.status === "review" && (
        <div className="mt-3.5 flex gap-2">
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => decide("approve")}
            className="flex-1 rounded-full bg-navy-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-navy-800 disabled:opacity-50 sm:flex-none"
          >
            {busy === "approve" ? "Approving…" : "Approve"}
          </button>
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => decide("dismiss")}
            className="flex-1 rounded-full border border-line bg-white px-4 py-2 text-sm font-medium text-navy-900 transition hover:border-navy-500 disabled:opacity-50 sm:flex-none"
          >
            {busy === "dismiss" ? "Dismissing…" : "Dismiss"}
          </button>
        </div>
      )}
      {error && <p className="mt-2 text-sm text-coral">{error}</p>}
    </li>
  );
}

function InjectPanel({ customerId, onUpdated }: { customerId: number; onUpdated: (d: CustomerDetail) => void }) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [kind, setKind] = useState<Signal["kind"]>("transaction");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");

  async function send(signal: SignalCreate, tag: string) {
    setBusy(tag);
    setError(null);
    try {
      onUpdated(await injectSignal(customerId, signal));
      if (tag === "custom") {
        setDescription("");
        setAmount("");
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const text = description.trim();
    if (!text) return;
    const parsed = amount.trim() === "" ? null : Number(amount.replace(",", "."));
    if (parsed !== null && !Number.isFinite(parsed)) {
      setError("Enter the amount as a number, for example -250.");
      return;
    }
    send({ kind, description: text.slice(0, 200), amount: parsed }, "custom");
  }

  return (
    <section className="rounded-[var(--radius-card)] bg-navy-900 p-4 text-white sm:p-5">
      <h2 className="font-display text-lg font-semibold tracking-tight">Add a signal</h2>
      <p className="mt-1 text-sm text-ice/65">Foresight re-analyzes this customer as soon as it arrives.</p>
      <div className="mt-4 grid grid-cols-2 gap-2">
        {PRESETS.map((p) => (
          <button
            key={p.label}
            type="button"
            disabled={busy !== null}
            onClick={() => send(p.signal, p.label)}
            className="flex flex-col items-start gap-2 rounded-2xl bg-white/[0.07] p-3 text-left text-sm transition hover:bg-white/[0.13] disabled:opacity-50"
          >
            {busy === p.label ? <Spinner className="size-4 text-cyan-300" /> : <p.icon className="size-4 text-cyan-300" aria-hidden />}
            <span className="font-medium leading-tight">{p.label}</span>
            {p.signal.amount != null && <span className="tabular text-xs text-ice/60">{signedMoney(p.signal.amount)}</span>}
          </button>
        ))}
      </div>

      {busy && (
        <p role="status" className="mt-3 flex items-center gap-2 rounded-xl bg-cyan-500/15 px-3 py-2.5 text-sm text-cyan-300">
          <Spinner className="size-4" />
          Reading the new signal and re-running the forecast…
        </p>
      )}

      <form onSubmit={onSubmit} className="mt-4 space-y-2.5 border-t border-white/10 pt-4">
        <div className="grid grid-cols-[minmax(0,1fr)_7rem] gap-2">
          <label className="sr-only" htmlFor="sig-kind">
            Kind
          </label>
          <select
            id="sig-kind"
            value={kind}
            onChange={(e) => setKind(e.target.value as Signal["kind"])}
            className="rounded-xl border border-white/15 bg-navy-800 px-3 py-2.5 text-sm text-white"
          >
            {(Object.keys(SIGNAL_KIND_LABEL) as Signal["kind"][]).map((k) => (
              <option key={k} value={k}>
                {SIGNAL_KIND_LABEL[k]}
              </option>
            ))}
          </select>
          <label className="sr-only" htmlFor="sig-amount">
            Amount in euro
          </label>
          <input
            id="sig-amount"
            inputMode="decimal"
            placeholder="€ amount"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="tabular rounded-xl border border-white/15 bg-navy-800 px-3 py-2.5 text-sm text-white placeholder:text-ice/40"
          />
        </div>
        <label className="sr-only" htmlFor="sig-desc">
          Description
        </label>
        <input
          id="sig-desc"
          maxLength={200}
          placeholder="Description, e.g. Deposit — Immo Vandenberghe"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full rounded-xl border border-white/15 bg-navy-800 px-3 py-2.5 text-sm text-white placeholder:text-ice/40"
        />
        <button
          type="submit"
          disabled={busy !== null || !description.trim()}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-navy-950 transition hover:bg-cyan-400 disabled:opacity-40"
        >
          {busy === "custom" && <Spinner className="size-4" />}
          Add signal
        </button>
      </form>
      {error && <p className="mt-3 rounded-xl bg-coral/20 px-3 py-2 text-sm text-[#ffc7b5]">{error}</p>}
    </section>
  );
}

function SignalTimeline({ signals, highlight }: { signals: Signal[]; highlight?: number }) {
  const [showAll, setShowAll] = useState(false);
  const visible = showAll ? signals : signals.slice(0, 8);
  return (
    <div>
      <ol className="relative space-y-3 border-l border-line pl-4">
        {visible.map((s) => (
          <li key={s.id} className={clsx("relative rounded-xl", s.id === highlight && "flash-change bg-ice p-2 -ml-2 pl-2")}>
            <span
              className={clsx(
                "absolute top-1.5 size-2.5 rounded-full border-2 border-white",
                s.id === highlight ? "-left-[1.3rem] bg-cyan-500" : "-left-[1.3rem] bg-navy-500",
              )}
            />
            <div className="flex items-baseline justify-between gap-2 text-xs text-muted">
              <span>
                {dayMonth(s.date)}, {SIGNAL_KIND_LABEL[s.kind]}
              </span>
              {s.amount != null && (
                <span className={clsx("tabular font-medium", s.amount > 0 ? "text-mint" : "text-ink")}>{signedMoney(s.amount)}</span>
              )}
            </div>
            <p className="mt-0.5 text-sm leading-snug text-ink">{s.description}</p>
          </li>
        ))}
      </ol>
      {signals.length > 8 && (
        <button type="button" onClick={() => setShowAll((v) => !v)} className="mt-3 text-sm font-medium text-navy-700">
          {showAll ? "Show fewer" : `Show all ${signals.length}`}
        </button>
      )}
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading customer">
      <Skeleton className="h-4 w-28" />
      <Skeleton className="mt-4 h-9 w-56" />
      <Skeleton className="mt-2 h-4 w-32" />
      <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="flex flex-col gap-5">
          <Skeleton className="h-72 w-full rounded-[var(--radius-card)]" />
          <Skeleton className="h-80 w-full rounded-[var(--radius-card)]" />
        </div>
        <Skeleton className="h-96 w-full rounded-[var(--radius-card)]" />
      </div>
    </div>
  );
}
