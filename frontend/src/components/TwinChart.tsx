"use client";

import clsx from "clsx";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { money, monthLong, monthShort, signedMoney } from "@/lib/format";
import type { Twin } from "@/lib/types";

const BUFFER = 250;

interface Point {
  x: number;
  y: number;
}

// Monotone cubic interpolation (Fritsch–Carlson): smooth, never overshoots a data point.
function smoothPath(points: Point[]) {
  if (points.length < 2) return "";
  const n = points.length;
  const dx = points.slice(1).map((p, i) => p.x - points[i].x);
  const slope = points.slice(1).map((p, i) => (p.y - points[i].y) / dx[i]);
  const m = points.map((_, i) => {
    if (i === 0) return slope[0];
    if (i === n - 1) return slope[n - 2];
    return slope[i - 1] * slope[i] <= 0 ? 0 : (slope[i - 1] + slope[i]) / 2;
  });
  for (let i = 0; i < n - 1; i++) {
    if (slope[i] === 0) {
      m[i] = 0;
      m[i + 1] = 0;
      continue;
    }
    const a = m[i] / slope[i];
    const b = m[i + 1] / slope[i];
    const h = a * a + b * b;
    if (h > 9) {
      const t = 3 / Math.sqrt(h);
      m[i] = t * a * slope[i];
      m[i + 1] = t * b * slope[i];
    }
  }
  let d = `M${points[0].x},${points[0].y}`;
  for (let i = 0; i < n - 1; i++) {
    const p = points[i];
    const q = points[i + 1];
    const h = dx[i] / 3;
    d += ` C${p.x + h},${p.y + m[i] * h} ${q.x - h},${q.y - m[i + 1] * h} ${q.x},${q.y}`;
  }
  return d;
}

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.round(entry.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, width] as const;
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
  const [wrapRef, width] = useWidth<HTMLDivElement>();
  const pinchMonths = useMemo(() => new Set(twin.pinch_points.map((p) => p.month)), [twin]);
  // The selection resets to the first pinch month whenever a new forecast arrives.
  const defaultMonth = twin.pinch_points[0]?.month ?? null;
  const [pick, setPick] = useState<{ twin: Twin; month: string | null }>({ twin, month: defaultMonth });
  const selected = pick.twin === twin ? pick.month : defaultMonth;
  const setSelected = (month: string | null) => setPick({ twin, month });

  const dark = variant === "dark";
  const pad = { top: 28, right: 14, bottom: 26, left: 14 };
  const w = Math.max(width, 280);
  const innerW = w - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;

  const values = [twin.start_balance, ...twin.months.map((m) => m.balance)];
  const lo = Math.min(0, ...values);
  const hi = Math.max(BUFFER * 4, ...values);
  const span = hi - lo || 1;
  const yMin = lo - span * 0.12;
  const yMax = hi + span * 0.08;

  const x = (i: number) => pad.left + (innerW * i) / twin.months.length;
  const y = (v: number) => pad.top + innerH * (1 - (v - yMin) / (yMax - yMin));

  const points = values.map((v, i) => ({ x: x(i), y: y(v) }));
  const line = smoothPath(points);
  const area = `${line} L${points.at(-1)!.x},${pad.top + innerH} L${points[0].x},${pad.top + innerH} Z`;
  const bufferY = y(BUFFER);
  const zeroY = y(0);
  const step = innerW / twin.months.length;
  const labelEvery = step < 34 ? 2 : 1;

  // Mark a life-moment estimate only in the month it first appears (a new mortgage, not every payment).
  const momentStarts = new Set<string>();
  const seenMoment = new Set<string>();
  for (const m of twin.months) {
    for (const e of m.events) {
      if (e.source === "moment" && !seenMoment.has(e.label)) {
        seenMoment.add(e.label);
        momentStarts.add(m.month);
      }
    }
  }

  const selectedMonth = twin.months.find((m) => m.month === selected);
  const selectedPinch = twin.pinch_points.find((p) => p.month === selected);
  const notable = selectedMonth?.events.filter((e) => e.source !== "recurring") ?? [];

  const c = dark
    ? {
        line: "#4cc6ee",
        areaTop: "rgba(76,198,238,0.32)",
        grid: "rgba(255,255,255,0.10)",
        text: "rgba(234,246,252,0.62)",
        buffer: "rgba(234,246,252,0.45)",
        dot: "#06224a",
        danger: "rgba(228,87,46,0.16)",
      }
    : {
        line: "#0b3a73",
        areaTop: "rgba(31,182,232,0.22)",
        grid: "#e4ebf3",
        text: "#5b6f88",
        buffer: "#8aa0b8",
        dot: "#ffffff",
        danger: "rgba(228,87,46,0.08)",
      };

  return (
    <div className={clsx("w-full", className)}>
      <div ref={wrapRef} className="relative w-full" style={{ height }}>
        {width > 0 && (
          <svg
            width={w}
            height={height}
            viewBox={`0 0 ${w} ${height}`}
            role="img"
            aria-label={`Forecast of your balance over the next ${twin.months.length} months`}
            className="block overflow-visible"
          >
            <defs>
              <linearGradient id={`area-${uid}`} x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={c.areaTop} />
                <stop offset="100%" stopColor={c.areaTop} stopOpacity="0" />
              </linearGradient>
              <clipPath id={`below-${uid}`}>
                <rect x={0} y={bufferY} width={w} height={height - bufferY} />
              </clipPath>
            </defs>

            {/* The zone under the €250 buffer: where money gets tight. */}
            <rect x={pad.left} y={bufferY} width={innerW} height={pad.top + innerH - bufferY} fill={c.danger} rx={6} />
            {lo < 0 && <line x1={pad.left} x2={w - pad.right} y1={zeroY} y2={zeroY} stroke={c.grid} />}

            <path d={area} fill={`url(#area-${uid})`} />
            <path d={line} fill="none" stroke={c.line} strokeWidth={2.5} strokeLinecap="round" />
            <path d={line} fill="none" stroke="#e4572e" strokeWidth={2.5} clipPath={`url(#below-${uid})`} />

            <line
              x1={pad.left}
              x2={w - pad.right}
              y1={bufferY}
              y2={bufferY}
              stroke={c.buffer}
              strokeDasharray="4 5"
              strokeWidth={1.25}
            />
            <text x={w - pad.right} y={bufferY - 6} textAnchor="end" fontSize={10.5} fill={c.text}>
              €250 buffer
            </text>

            {twin.months.map((m, i) => {
              const px = x(i + 1);
              const py = y(m.balance);
              const isPinch = pinchMonths.has(m.month);
              const hasMoment = momentStarts.has(m.month);
              const isSelected = selected === m.month;
              return (
                <g key={m.month}>
                  {isSelected && (
                    <line x1={px} x2={px} y1={pad.top - 8} y2={pad.top + innerH} stroke={c.grid} strokeWidth={1.5} />
                  )}
                  {hasMoment && !isPinch && (
                    <rect
                      x={px - 4.5}
                      y={py - 4.5}
                      width={9}
                      height={9}
                      transform={`rotate(45 ${px} ${py})`}
                      fill={c.dot}
                      stroke="#1fb6e8"
                      strokeWidth={2}
                    />
                  )}
                  {isPinch && (
                    <>
                      <circle cx={px} cy={py} r={11} fill="#e4572e" opacity={0.18}>
                        <animate attributeName="r" values="7;14;7" dur="2.4s" repeatCount="3" />
                      </circle>
                      <circle cx={px} cy={py} r={5.5} fill="#e4572e" stroke={c.dot} strokeWidth={2} />
                      <g transform={`translate(${Math.min(Math.max(px, 44), w - 44)}, ${Math.max(py - 18, 12)})`}>
                        <rect x={-38} y={-12} width={76} height={20} rx={10} fill="#e4572e" />
                        <text textAnchor="middle" y={2} fontSize={11} fontWeight={600} fill="#fff">
                          {money(m.balance)}
                        </text>
                      </g>
                    </>
                  )}
                  {((i % labelEvery === 0 && (i > 0 || step >= 40)) || isPinch) && (
                    <text
                      x={px}
                      y={height - 6}
                      textAnchor="middle"
                      fontSize={10.5}
                      fontWeight={isPinch || isSelected ? 700 : 400}
                      fill={isPinch ? "#e4572e" : c.text}
                    >
                      {monthShort(m.month)}
                    </text>
                  )}
                  <rect
                    x={px - innerW / twin.months.length / 2}
                    y={0}
                    width={innerW / twin.months.length}
                    height={height}
                    fill="transparent"
                    className="cursor-pointer"
                    onClick={() => setSelected(isSelected ? null : m.month)}
                  >
                    <title>{`${monthLong(m.month)}: ${money(m.balance)}`}</title>
                  </rect>
                </g>
              );
            })}
            <circle cx={points[0].x} cy={points[0].y} r={4} fill={c.line} />
            <text x={points[0].x} y={height - 6} fontSize={10.5} fill={c.text}>
              Now
            </text>
          </svg>
        )}
      </div>

      <div
        className={clsx(
          "mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px]",
          dark ? "text-ice/60" : "text-muted",
        )}
      >
        <span className="inline-flex items-center gap-1.5">
          <span className={clsx("h-0.5 w-4 rounded", dark ? "bg-cyan-400" : "bg-navy-700")} /> Balance
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="size-2 rotate-45 border-2 border-cyan-500" /> Life-moment estimate
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="size-2 rounded-full bg-coral" /> Below buffer
        </span>
      </div>

      {selectedMonth && (
        <div
          className={clsx(
            "mt-3 rounded-2xl p-3.5 text-sm",
            dark ? "bg-white/[0.07] text-ice" : "border border-line bg-white",
          )}
        >
          <div className="flex items-baseline justify-between gap-3">
            <span className="font-semibold">{monthLong(selectedMonth.month)}</span>
            <span className={clsx("tabular font-semibold", selectedPinch && "text-coral")}>
              {money(selectedMonth.balance)}
            </span>
          </div>
          {selectedPinch && (
            <p className={clsx("mt-1.5 leading-snug", dark ? "text-ice/80" : "text-muted")}>{selectedPinch.reason}</p>
          )}
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
          {!selectedPinch && notable.length === 0 && (
            <p className={clsx("mt-1", dark ? "text-ice/60" : "text-muted")}>Only your usual income and bills.</p>
          )}
        </div>
      )}
    </div>
  );
}
