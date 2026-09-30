import clsx from "clsx";
import { MOMENTS, percent, STATUS_LABEL } from "@/lib/format";
import type { Intervention, MomentKey } from "@/lib/types";

export const MOMENT_TONE: Record<MomentKey, string> = {
  moving_home: "bg-ice text-navy-700",
  growing_family: "bg-ice text-navy-700",
  new_job: "bg-ice text-navy-700",
  approaching_retirement: "bg-ice text-navy-700",
  buying_car: "bg-ice text-navy-700",
  travel_abroad: "bg-ice text-navy-700",
  financial_stress: "bg-coral-soft text-coral",
  no_clear_moment: "bg-[#eef2f6] text-muted",
};

export function MomentChip({ moment, confidence }: { moment: MomentKey | null; confidence?: number | null }) {
  if (!moment) return <span className="text-sm text-muted">Not analyzed</span>;
  return (
    <span className={clsx("inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium", MOMENT_TONE[moment])}>
      {MOMENTS[moment].label}
      {confidence != null && <span className="tabular opacity-70">{percent(confidence)}</span>}
    </span>
  );
}

/** Stress as a five-segment meter: quick to scan down a column. */
export function StressMeter({ value }: { value: number | null }) {
  if (value == null) return <span className="text-sm text-muted">–</span>;
  const filled = Math.round(value * 5);
  const high = value >= 0.6;
  return (
    <span className="inline-flex items-center gap-2" title={`Stress ${percent(value)}`}>
      <span className="flex gap-0.5" aria-hidden>
        {Array.from({ length: 5 }, (_, i) => (
          <span
            key={i}
            className={clsx("h-3 w-1.5 rounded-sm", i < filled ? (high ? "bg-coral" : "bg-navy-500") : "bg-line")}
          />
        ))}
      </span>
      <span className={clsx("tabular text-xs", high ? "font-semibold text-coral" : "text-muted")}>{percent(value)}</span>
    </span>
  );
}

export const STATUS_TONE: Record<Intervention["status"], string> = {
  delivered: "bg-mint-soft text-mint",
  review: "bg-amber-soft text-amber",
  held: "bg-[#eef2f6] text-muted",
  dismissed: "bg-[#eef2f6] text-muted line-through decoration-muted/40",
};

export function StatusBadge({ status }: { status: Intervention["status"] }) {
  return (
    <span className={clsx("whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium", STATUS_TONE[status])}>
      {STATUS_LABEL[status]}
    </span>
  );
}

export function Panel({
  title,
  aside,
  children,
  className,
  flash,
  thinking,
}: {
  title: string;
  aside?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  flash?: boolean;
  /** The model is rewriting this panel: dim it and say so. */
  thinking?: boolean;
}) {
  return (
    <section
      aria-busy={thinking || undefined}
      className={clsx(
        "relative overflow-hidden rounded-[var(--radius-card)] border bg-white p-4 transition-colors sm:p-5",
        thinking ? "border-cyan-500/50" : "border-line",
        flash && "flash-change",
        className,
      )}
    >
      {thinking && (
        <div aria-hidden className="thinking-sheen pointer-events-none absolute inset-0 z-10">
          <span className="absolute right-4 top-4 inline-flex items-center gap-2 rounded-full bg-navy-900 px-3 py-1 text-xs font-medium text-white shadow-lg">
            <span className="size-1.5 animate-pulse rounded-full bg-cyan-400" />
            Re-analyzing
          </span>
        </div>
      )}
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-display text-lg font-semibold tracking-tight text-navy-900">{title}</h2>
        {aside}
      </div>
      <div className="mt-3">{children}</div>
    </section>
  );
}
