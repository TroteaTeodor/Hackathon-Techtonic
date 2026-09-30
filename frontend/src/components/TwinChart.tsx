"use client";

import clsx from "clsx";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import {
  Area,
  ComposedChart,
  ReferenceArea,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from "recharts";
import { useInView } from "@/components/motion";
import { money, monthLong, monthShort, signedMoney } from "@/lib/format";
import type { Twin } from "@/lib/types";

const BUFFER = 250;
const CORAL = "#e4572e";

interface Point {
  key: string; // "now" or YYYY-MM
  balance: number;
}

export function TwinChart({
  twin,
  variant = "light",
  height = 220,
  className,
}: {
  twin: Twin;
  variant?: "light" | "dark";
  height?: number;
  className?: string;
}) {
  const uid = useId().replace(/:/g, "");
  const dark = variant === "dark";
  const [viewRef, inView] = useInView<HTMLDivElement>(0.4);

  const data: Point[] = useMemo(
    () => [{ key: "now", balance: twin.start_balance }, ...twin.months.map((m) => ({ key: m.month, balance: m.balance }))],
    [twin],
  );

  // Mark a life-moment estimate only in the month it first appears (a new mortgage, not every payment).
  const momentStarts = useMemo(() => {
    const seen = new Set<string>();
    const starts: string[] = [];
    for (const m of twin.months) {
      for (const e of m.events) {
        if (e.source === "moment" && !seen.has(e.label)) {
          seen.add(e.label);
          if (!starts.includes(m.month)) starts.push(m.month);
        }
      }
    }
    return starts;
  }, [twin]);

  const pinchMonths = new Set(twin.pinch_points.map((p) => p.month));
  const defaultMonth = twin.pinch_points[0]?.month ?? null;

  // Hover follows the pointer; a tap pins a month. Both reset when a new forecast arrives.
  const [hover, setHover] = useState<string | null>(null);
  const [pin, setPin] = useState<{ twin: Twin; month: string | null }>({ twin, month: defaultMonth });
  const pinned = pin.twin === twin ? pin.month : defaultMonth;
  const shown = hover && hover !== "now" ? hover : pinned;

  const values = data.map((d) => d.balance);
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = Math.max(hi - lo, 1);
  const yMin = Math.min(0, lo) - Math.max(span * 0.12, 150);
  // Keep the buffer line in frame without leaving a tall empty band above a low forecast.
  const yMax = Math.max(hi, BUFFER) + Math.max(span * 0.12, 300);
  // Where the €250 buffer sits inside the line's own bounding box, for the two-colour stroke.
  const split = hi === lo ? 0 : Math.min(Math.max((hi - BUFFER) / (hi - lo), 0), 1);

  const c = dark
    ? {
        line: "#4cc6ee",
        area: "rgba(76,198,238,0.30)",
        text: "rgba(234,246,252,0.62)",
        buffer: "rgba(234,246,252,0.45)",
        dot: "#06224a",
        zone: "rgba(228,87,46,0.14)",
        cursor: "rgba(234,246,252,0.35)",
      }
    : {
        line: "#0b3a73",
        area: "rgba(31,182,232,0.22)",
        text: "#5b6f88",
        buffer: "#8aa0b8",
        dot: "#ffffff",
        zone: "rgba(228,87,46,0.07)",
        cursor: "#8aa0b8",
      };

  const selectedMonth = twin.months.find((m) => m.month === shown);

  return (
    <div className={clsx("w-full select-none", className)}>
      <div ref={viewRef} style={{ height }} className="touch-pan-y">
        {inView && (
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={data}
            margin={{ top: 26, right: 12, bottom: 0, left: 12 }}
            onMouseMove={(state) => {
              const label = (state as { activeLabel?: string | number }).activeLabel;
              setHover(label == null ? null : String(label));
            }}
            onMouseLeave={() => setHover(null)}
            onClick={(state) => {
              const label = (state as { activeLabel?: string | number }).activeLabel;
              if (label != null && label !== "now") setPin({ twin, month: String(label) });
            }}
          >
            <defs>
              <linearGradient id={`stroke-${uid}`} x1="0" x2="0" y1="0" y2="1">
                <stop offset={split} stopColor={c.line} />
                <stop offset={split} stopColor={CORAL} />
              </linearGradient>
              <linearGradient id={`fill-${uid}`} x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={c.area} />
                <stop offset="100%" stopColor={c.area} stopOpacity={0} />
              </linearGradient>
            </defs>

            <XAxis
              dataKey="key"
              axisLine={false}
              tickLine={false}
              interval="preserveStartEnd"
              minTickGap={14}
              tick={{ fontSize: 10.5, fill: c.text }}
              tickFormatter={(k: string) => (k === "now" ? "Now" : monthShort(k))}
            />
            <YAxis hide domain={[yMin, yMax]} />

            <ReferenceArea y1={yMin} y2={BUFFER} fill={c.zone} strokeOpacity={0} ifOverflow="hidden" />
            {lo < 0 && <ReferenceLine y={0} stroke={c.buffer} strokeOpacity={0.35} />}
            <ReferenceLine
              y={BUFFER}
              stroke={c.buffer}
              strokeDasharray="4 5"
              label={{ value: "€250 buffer", position: "insideTopRight", fill: c.text, fontSize: 10.5 }}
            />

            <Tooltip
              cursor={{ stroke: c.cursor, strokeWidth: 1.5, strokeDasharray: "3 3" }}
              content={(props) => <ChartTip {...(props as TooltipContentProps)} dark={dark} />}
              isAnimationActive={false}
              wrapperStyle={{ outline: "none" }}
            />

            <Area
              type="monotone"
              dataKey="balance"
              stroke={hi < BUFFER ? CORAL : lo >= BUFFER ? c.line : `url(#stroke-${uid})`}
              strokeWidth={2.5}
              fill={`url(#fill-${uid})`}
              dot={false}
              activeDot={(p: { cx?: number; cy?: number; payload?: Point }) => (
                <circle
                  cx={p.cx}
                  cy={p.cy}
                  r={6}
                  fill={(p.payload?.balance ?? 0) < BUFFER ? CORAL : c.line}
                  stroke={c.dot}
                  strokeWidth={2.5}
                />
              )}
              animationBegin={150}
              animationDuration={1600}
              animationEasing="ease-out"
            />

            {momentStarts
              .filter((m) => !pinchMonths.has(m))
              .map((m) => (
                <ReferenceDot
                  key={`moment-${m}`}
                  x={m}
                  y={data.find((d) => d.key === m)!.balance}
                  shape={(p: { cx?: number; cy?: number }) => (
                    <rect
                      x={(p.cx ?? 0) - 4.5}
                      y={(p.cy ?? 0) - 4.5}
                      width={9}
                      height={9}
                      transform={`rotate(45 ${p.cx} ${p.cy})`}
                      fill={c.dot}
                      stroke="#1fb6e8"
                      strokeWidth={2}
                    />
                  )}
                />
              ))}

            {twin.pinch_points.map((p, i) => (
              <ReferenceDot
                key={`pinch-${p.month}`}
                x={p.month}
                y={p.balance}
                shape={(d: { cx?: number; cy?: number }) =>
                  i > 0 ? (
                    // Later tight months: a quiet dot, so a long tight stretch doesn't stack labels.
                    <circle cx={d.cx} cy={d.cy} r={3.5} fill={CORAL} stroke={c.dot} strokeWidth={1.5} />
                  ) : (
                  <g>
                    <circle cx={d.cx} cy={d.cy} r={12} fill={CORAL} opacity={0.18} />
                    <circle cx={d.cx} cy={d.cy} r={5.5} fill={CORAL} stroke={c.dot} strokeWidth={2} />
                    <g transform={`translate(${d.cx}, ${(d.cy ?? 0) - 20})`}>
                      <rect x={-36} y={-11} width={72} height={20} rx={10} fill={CORAL} />
                      <text textAnchor="middle" y={3} fontSize={11} fontWeight={600} fill="#fff">
                        {money(p.balance)}
                      </text>
                    </g>
                  </g>
                  )
                }
              />
            ))}
          </ComposedChart>
        </ResponsiveContainer>
        )}
      </div>

      <div className={clsx("mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px]", dark ? "text-ice/60" : "text-muted")}>
        <span className="inline-flex items-center gap-1.5">
          <span className={clsx("h-0.5 w-4 rounded", dark ? "bg-cyan-400" : "bg-navy-700")} /> Balance
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="size-2 rotate-45 border-2 border-cyan-500" /> Life-moment estimate
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="size-2 rounded-full bg-coral" /> Below buffer
        </span>
        <span className="ml-auto hidden sm:inline">Hover or tap a month</span>
      </div>

      {/* The box is exactly as tall as the chosen month and eases to the next month's height, so a
          month with more lines expands smoothly instead of jumping. Only the chosen month is in flow;
          the others wait out of flow, invisible, ready to crossfade in. */}
      <MonthBox dark={dark}>
        <div
          className={clsx(
            "min-w-0 transition-opacity duration-200",
            selectedMonth ? "invisible absolute inset-x-3.5 top-3.5 opacity-0" : "relative opacity-100",
            dark ? "text-ice/60" : "text-muted",
          )}
        >
          Hover or tap a month to see what happens in it.
        </div>
        {twin.months.map((m) => (
          <MonthDetails
            key={m.month}
            month={m}
            pinch={twin.pinch_points.find((p) => p.month === m.month)}
            dark={dark}
            active={m.month === shown}
          />
        ))}
      </MonthBox>
    </div>
  );
}

/** A panel whose height follows its content with an eased transition. */
function MonthBox({ dark, children }: { dark: boolean; children: React.ReactNode }) {
  const inner = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number | null>(null);
  useEffect(() => {
    const el = inner.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setHeight(Math.ceil(entry.borderBoxSize[0]?.blockSize ?? el.offsetHeight)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return (
    <div
      aria-live="polite"
      style={height == null ? undefined : { height }}
      className={clsx(
        "month-box mt-3 overflow-hidden rounded-2xl text-sm transition-[height] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]",
        dark ? "bg-white/[0.07] text-ice" : "border border-line bg-white",
      )}
    >
      <div ref={inner} className="relative p-3.5">
        {children}
      </div>
    </div>
  );
}

function MonthDetails({
  month,
  pinch,
  dark,
  active,
}: {
  month: Twin["months"][number];
  pinch?: Twin["pinch_points"][number];
  dark: boolean;
  active: boolean;
}) {
  const notable = month.events.filter((e) => e.source !== "recurring");
  return (
    <div
      aria-hidden={!active}
      className={clsx(
        "min-w-0 transition-[opacity,transform] duration-200 ease-out",
        active ? "relative translate-y-0 opacity-100" : "invisible absolute inset-x-3.5 top-3.5 translate-y-0.5 opacity-0",
      )}
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-semibold">{monthLong(month.month)}</span>
        <span className={clsx("tabular font-semibold", month.balance < BUFFER && "text-coral")}>{money(month.balance)}</span>
      </div>
      {pinch && <p className={clsx("mt-1.5 leading-snug", dark ? "text-ice/80" : "text-muted")}>{pinch.reason}</p>}
      {notable.length > 0 && (
        <ul className="mt-2 space-y-1">
          {notable.map((e) => (
            <li key={e.label} className="flex items-center justify-between gap-3">
              <span className="flex min-w-0 items-center gap-2">
                {e.source === "moment" ? (
                  <span className="size-1.5 shrink-0 rotate-45 border-[1.5px] border-cyan-500" />
                ) : (
                  <span className={clsx("size-1.5 shrink-0 rounded-full", dark ? "bg-ice/50" : "bg-muted/60")} />
                )}
                <span className="truncate">{e.label}</span>
              </span>
              <span className="tabular shrink-0">{signedMoney(e.amount)}</span>
            </li>
          ))}
        </ul>
      )}
      {!pinch && notable.length === 0 && (
        <p className={clsx("mt-1", dark ? "text-ice/60" : "text-muted")}>Only your usual income and bills.</p>
      )}
    </div>
  );
}

function ChartTip({ active, payload, label, dark }: TooltipContentProps & { dark: boolean }) {
  const point = payload?.[0]?.payload as Point | undefined;
  if (!active || !point) return null;
  const below = point.balance < BUFFER;
  return (
    <div
      className={clsx(
        "rounded-xl px-3 py-2 text-xs shadow-[0_10px_30px_-12px_rgba(4,24,51,0.55)]",
        dark ? "bg-white text-navy-900" : "bg-navy-900 text-white",
      )}
    >
      <div className={clsx(dark ? "text-muted" : "text-ice/70")}>{label === "now" ? "Today" : monthLong(String(label))}</div>
      <div className={clsx("tabular mt-0.5 text-sm font-semibold", below && "text-coral")}>{money(point.balance)}</div>
    </div>
  );
}
