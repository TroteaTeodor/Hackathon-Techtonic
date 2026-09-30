"use client";

import clsx from "clsx";
import Link from "next/link";
import { useId } from "react";
import { scrollToTop } from "@/components/motion";

/**
 * KBC's logo, drawn from the official SVG (Wikimedia Commons "KBC logo.svg"): the cyan sun over the
 * wave, and the KBC letters. Colours and proportions are untouched; on dark backgrounds the letters
 * switch to white, the usual reverse version.
 */
export function KbcLogo({ tone = "light", className, intro = false }: { tone?: "light" | "dark"; className?: string; intro?: boolean }) {
  const letters = tone === "light" ? "#ffffff" : "#0d2a50";
  return (
    <svg viewBox="0 0 256.01 199.69" role="img" aria-label="KBC" className={clsx("block", className)}>
      <circle cx="129.48" cy="44.2" r="44.2" fill="#0097db" className={clsx(intro && "kbc-sun")} />
      <path
        className={clsx(intro && "kbc-wave")}
        d="m 162.07,79.970002 c -8.42,9.13 -23.27,18.26 -42.32,18.26 -14.78,0 -27.51,-5.75 -35.61,-12.13 -48.25,5.06 -84.14,12.24 -84.14,12.24 V 117.88 l 255.99,-0.03 V 77.560002 c 0,0 -43.86,-0.27 -93.92,2.41 z"
        fill="#0097db"
      />
      <g fill={letters} className={clsx(intro && "kbc-letters")}>
        <path d="m 30.42,175.01 v 23.81 H 0.01 v -63.34 h 30.41 v 28.5 h 0.18 l 17.9,-28.5 h 36.46 l -26.7,32.74 25.2,30.6 H 48.66 L 30.64,175.01 Z" />
        <path d="m 256.01,196.2 c -7.18,2.19 -16.61,3.49 -25.05,3.49 -30.08,0 -52.18,-8.55 -52.18,-33.42 0,-22.48 21.41,-32.24 50.68,-32.24 8.13,0 18.47,0.9 26.55,3.48 v 21.77 c -6,-3.63 -11.990,-5.89 -20.57,-5.89 -11.17,0 -22.32,5.5 -22.32,13.48 0,7.98 11.11,13.48 22.32,13.48 8.44,0 14.57,-2.34 20.56,-5.8 v 21.66 h 0.01 z" />
        <path d="m 89.94,135.48 h 61.48 c 15.97,0 21.2,6.21 21.2,15.88 0,10.82 -9.670,15.52 -19.61,16.06 v 0.18 c 10.2,0.8 20.14,1.95 20.14,14.72 0,8.34 -5.23,16.5 -22.79,16.5 H 89.95 v -63.34 z m 30.41,50.46 h 15.86 c 5.95,0 7.97,-2.46 7.97,-6.1 0,-3.64 -2.04,-6.25 -7.9,-6.25 h -15.92 v 12.35 z m 0,-23.62 h 15.15 c 5.85,0 8.15,-2.37 8.15,-6.01 0,-4.17 -2.31,-6.25 -7.72,-6.25 h -15.57 v 12.26 0 z" />
      </g>
    </svg>
  );
}

/**
 * Foresight's mark: an eye drawn as a vesica (the overlap of two r=18 circles), with a sun for a
 * pupil — fore-sight, seeing what's ahead, in KBC's cyan.
 */
export function ForesightMark({ className }: { tone?: "light" | "dark"; className?: string }) {
  const id = useId().replace(/:/g, "");
  return (
    <svg viewBox="2.2 9.6 27.6 12.8" className={clsx("w-auto shrink-0", className)} aria-hidden>
      <defs>
        <linearGradient id={`fs-g-${id}`} x1="3" y1="10" x2="29" y2="22" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#4fd0f7" />
          <stop offset="1" stopColor="#0097db" />
        </linearGradient>
      </defs>
      <path d="M2.58 16A18 18 0 0 1 29.42 16A18 18 0 0 1 2.58 16Z" fill={`url(#fs-g-${id})`} />
      <circle cx="16" cy="16" r="6.2" fill="#06224a" />
      <circle cx="16" cy="16" r="3.6" fill="#ffffff" />
    </svg>
  );
}

const SIZES = {
  sm: { kbc: "h-[26px]", mark: "h-[15px]", word: "text-[17px]", gap: "gap-2.5", rule: "h-6" },
  md: { kbc: "h-8", mark: "h-[18px]", word: "text-lg", gap: "gap-3", rule: "h-7" },
  lg: { kbc: "h-11", mark: "h-6", word: "text-2xl", gap: "gap-4", rule: "h-10" },
} as const;

/**
 * The co-brand lockup: KBC, a hairline, then Foresight. "light" is for navy backgrounds.
 * With `intro`, KBC's sun rises over the wave, the hairline draws and Foresight slides in (once).
 */
export function CoBrand({
  tone = "light",
  size = "sm",
  href,
  intro = false,
  className,
  label,
}: {
  tone?: "light" | "dark";
  size?: keyof typeof SIZES;
  href?: string | null;
  intro?: boolean;
  className?: string;
  /** Small text after the wordmark, e.g. "Advisor console". */
  label?: string;
}) {
  const s = SIZES[size];
  const body = (
    <>
      <KbcLogo tone={tone} intro={intro} className={clsx(s.kbc, "w-auto")} />
      <span
        aria-hidden
        className={clsx("w-px shrink-0 origin-bottom", s.rule, tone === "light" ? "bg-white/25" : "bg-navy-900/15", intro && "cobrand-rule")}
      />
      <span className={clsx("inline-flex items-center gap-2", intro && "cobrand-word")}>
        <ForesightMark tone={tone} className={s.mark} />
        <span
          className={clsx(
            "font-display font-semibold tracking-tight",
            s.word,
            tone === "light" ? "text-white" : "text-navy-900",
          )}
        >
          Foresight
        </span>
        {label && <span className={clsx("hidden text-sm sm:inline", tone === "light" ? "text-ice/60" : "text-muted")}>{label}</span>}
      </span>
    </>
  );
  const cls = clsx("inline-flex items-center", s.gap, className);
  if (!href) return <span className={cls}>{body}</span>;
  return (
    <Link
      href={href}
      aria-label="KBC Foresight home"
      className={clsx("press -m-1.5 rounded-xl p-1.5", cls)}
      onClick={(e) => {
        // Already on the home page: glide to the top instead of doing nothing.
        if (window.location.pathname === href) {
          e.preventDefault();
          scrollToTop();
        }
      }}
    >
      {body}
    </Link>
  );
}
