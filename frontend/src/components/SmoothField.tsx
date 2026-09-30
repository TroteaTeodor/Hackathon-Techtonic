"use client";

import clsx from "clsx";
import { motion } from "motion/react";
import { useId, useRef, useState, type ComponentProps, type ReactNode } from "react";

/**
 * A text field with smooth typing: each new character settles in and the caret glides to its
 * place instead of jumping. The real <input> stays underneath (transparent text, invisible
 * caret), so autofill, IME, selection, screen readers and mobile keyboards all behave natively;
 * only the drawing is ours.
 */
export function SmoothField({
  label,
  value,
  onValueChange,
  masked = false,
  invalid = false,
  trailing,
  hint,
  className,
  inputRef,
  onKeyUp,
  ...input
}: {
  label: string;
  value: string;
  onValueChange: (v: string) => void;
  /** Draw dots instead of the characters (passwords). */
  masked?: boolean;
  invalid?: boolean;
  trailing?: ReactNode;
  hint?: ReactNode;
  inputRef?: React.RefObject<HTMLInputElement | null>;
} & Omit<ComponentProps<"input">, "value" | "onChange" | "ref">) {
  const id = useId();
  const localRef = useRef<HTMLInputElement | null>(null);
  const ownRef = inputRef ?? localRef;
  const [focused, setFocused] = useState(false);
  const [sel, setSel] = useState<[number, number]>([0, 0]);
  const [scroll, setScroll] = useState(0);

  const sync = () => {
    const el = ownRef.current;
    if (!el) return;
    setSel([el.selectionStart ?? el.value.length, el.selectionEnd ?? el.value.length]);
    setScroll(el.scrollLeft);
  };

  const floated = focused || value.length > 0;
  const chars = Array.from(value);
  const [start, end] = sel;
  const collapsed = start === end;

  return (
    <div className={className}>
      <div
        className={clsx(
          "relative h-14 rounded-2xl border bg-white transition-[border-color,box-shadow] duration-200",
          invalid
            ? "border-coral/70 shadow-[0_0_0_4px_rgb(228_87_46/0.12)]"
            : focused
              ? "border-cyan-500 shadow-[0_0_0_4px_rgb(31_182_232/0.16)]"
              : "border-line hover:border-navy-500/35",
        )}
      >
        <label
          htmlFor={id}
          className={clsx(
            "pointer-events-none absolute left-4 top-1/2 origin-left -translate-y-1/2 transition-[transform,color] duration-200 ease-[cubic-bezier(0.16,1,0.3,1)]",
            floated ? "-translate-y-[1.35rem] scale-[0.78] text-muted" : "text-[15px] text-muted/90",
            focused && !invalid && "text-navy-700",
          )}
        >
          {label}
        </label>

        <input
          id={id}
          ref={ownRef}
          value={value}
          onChange={(e) => {
            onValueChange(e.target.value);
            requestAnimationFrame(sync);
          }}
          onSelect={sync}
          onKeyUp={(e) => {
            sync();
            onKeyUp?.(e);
          }}
          onFocus={() => {
            setFocused(true);
            requestAnimationFrame(sync);
          }}
          onBlur={() => setFocused(false)}
          aria-invalid={invalid || undefined}
          className={clsx(
            "smooth-input absolute inset-0 h-full w-full rounded-2xl bg-transparent pb-2 pl-4 pt-6 text-base outline-none",
            trailing ? "pr-12" : "pr-4",
          )}
          {...input}
        />

        {/* What you see: the characters and a gliding caret, drawn over the invisible input. */}
        <div
          aria-hidden
          className={clsx("pointer-events-none absolute inset-y-0 left-4 overflow-hidden pb-2 pt-6", trailing ? "right-12" : "right-4")}
        >
          <div className="flex h-full items-center whitespace-pre text-base text-ink" style={{ transform: `translateX(${-scroll}px)` }}>
            {chars.map((ch, i) => (
              <span key={i} className="relative">
                {focused && collapsed && start === i && <Caret id={id} />}
                <span
                  className={clsx(
                    "char-in",
                    !collapsed && i >= start && i < end && "rounded-[3px] bg-cyan-500/25",
                    masked && "mx-[0.5px] text-[1.15em] leading-none",
                  )}
                >
                  {masked ? "•" : ch === " " ? " " : ch}
                </span>
              </span>
            ))}
            {focused && collapsed && start >= chars.length && (
              <span className="relative">
                <Caret id={id} />
              </span>
            )}
          </div>
        </div>

        {trailing && <div className="absolute inset-y-0 right-1.5 flex items-center">{trailing}</div>}
      </div>
      {hint && <div className="mt-1.5 px-1 text-[13px]">{hint}</div>}
    </div>
  );
}

function Caret({ id }: { id: string }) {
  return (
    <motion.span
      layoutId={`caret-${id}`}
      transition={{ type: "spring", stiffness: 900, damping: 50, mass: 0.6 }}
      className="caret-blink absolute -left-px top-1/2 h-[1.3em] w-[2px] -translate-y-1/2 rounded-full bg-cyan-500"
    />
  );
}
