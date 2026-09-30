"use client";

import NumberFlow from "@number-flow/react";
import clsx from "clsx";
import Lenis from "lenis";
import "lenis/dist/lenis.css";
import { useEffect, useState } from "react";

/**
 * Inertial wheel scrolling on desktop. Touch keeps native scrolling, and reduced motion turns it off.
 * It pauses while a dialog locks the page (Radix sets data-scroll-locked on <body>), so the wheel
 * scrolls the dialog, never the page behind it. Scroll areas marked data-lenis-prevent keep native
 * scrolling.
 */
export function SmoothScroll() {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const lenis = new Lenis({ autoRaf: true, lerp: 0.11, wheelMultiplier: 0.95 });
    const sync = () => (document.body.hasAttribute("data-scroll-locked") ? lenis.stop() : lenis.start());
    const mo = new MutationObserver(sync);
    mo.observe(document.body, { attributes: true, attributeFilter: ["data-scroll-locked"] });
    return () => {
      mo.disconnect();
      lenis.destroy();
    };
  }, []);
  return null;
}

/** Euro amount whose digits roll to the new value when it changes. */
export function Money({ value, className }: { value: number; className?: string }) {
  return (
    <NumberFlow
      value={value}
      locales="en-GB"
      format={{ style: "currency", currency: "EUR", maximumFractionDigits: 0 }}
      className={clsx("tabular", className)}
    />
  );
}

export function Num({
  value,
  className,
  format,
}: {
  value: number;
  className?: string;
  format?: React.ComponentProps<typeof NumberFlow>["format"];
}) {
  return <NumberFlow value={value} locales="en-GB" format={format} className={clsx("tabular", className)} />;
}

/**
 * Text that arrives word by word, like a model writing it. Pure CSS, so it finishes even in a
 * background tab. Change `id` to replay it (for example when the analysis is re-run).
 */
export function StreamText({ text, id, className }: { text: string; id?: string; className?: string }) {
  const words = text.split(/(\s+)/);
  return (
    <span key={id ?? text} className={className} aria-label={text}>
      {words.map((w, i) =>
        /^\s+$/.test(w) ? (
          w
        ) : (
          <span key={i} aria-hidden className="stream-word" style={{ animationDelay: `${Math.min(i, 120) * 14}ms` }}>
            {w}
          </span>
        ),
      )}
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <span aria-hidden className={clsx("skeleton block rounded-lg", className)} />;
}

/**
 * True once the element has scrolled into view (and stays true), so entrances start when they can be
 * seen. Returns a callback ref, so it also works for elements that only appear after data loads.
 */
export function useInView<T extends Element>(threshold = 0.4) {
  const [el, setEl] = useState<T | null>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    if (!el || inView) return;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          io.disconnect();
        }
      },
      { threshold },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [el, inView, threshold]);
  return [setEl, inView] as const;
}

/** A number that rolls up from zero the first time it scrolls into view. */
export function RollIn({
  value,
  format,
  className,
}: {
  value: number;
  format?: React.ComponentProps<typeof NumberFlow>["format"];
  className?: string;
}) {
  const [ref, inView] = useInView<HTMLSpanElement>(0.5);
  return (
    <span ref={ref} className={className}>
      <Num value={inView ? value : 0} format={format} />
    </span>
  );
}
