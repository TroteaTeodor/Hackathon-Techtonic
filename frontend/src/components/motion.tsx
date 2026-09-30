"use client";

import NumberFlow from "@number-flow/react";
import clsx from "clsx";
import Lenis from "lenis";
import "lenis/dist/lenis.css";
import { useEffect, useRef, useState } from "react";

/** Inertial wheel scrolling on desktop. Touch keeps native scrolling, and reduced motion turns it off. */
export function SmoothScroll() {
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const lenis = new Lenis({ autoRaf: true, lerp: 0.11, wheelMultiplier: 0.95 });
    return () => lenis.destroy();
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

/** True once the element has scrolled into view (and stays true), so entrances start when they can be seen. */
export function useInView<T extends Element>(threshold = 0.4) {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
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
  }, [inView, threshold]);
  return [ref, inView] as const;
}
