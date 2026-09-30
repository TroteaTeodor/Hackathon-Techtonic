import clsx from "clsx";
import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

type Variant = "primary" | "accent" | "secondary" | "soft" | "ghost" | "ghost-dark";
type Size = "sm" | "md" | "lg";

const base =
  "relative inline-flex select-none items-center justify-center gap-2 whitespace-nowrap font-semibold " +
  "outline-none focus-visible:ring-4 disabled:cursor-not-allowed disabled:opacity-45 " +
  "transition-[background-color,border-color,color,box-shadow,transform] duration-200 ease-out";

const variants: Record<Variant, string> = {
  // The one main action on a screen: deep navy with a lit top edge.
  primary:
    "bg-navy-900 text-white shadow-[inset_0_1px_0_rgb(255_255_255/0.14),0_1px_2px_rgb(4_24_51/0.35),0_6px_16px_-6px_rgb(6_34_74/0.55)] " +
    "hover:bg-navy-800 hover:shadow-[inset_0_1px_0_rgb(255_255_255/0.18),0_2px_4px_rgb(4_24_51/0.35),0_10px_22px_-8px_rgb(6_34_74/0.6)] " +
    "focus-visible:ring-cyan-500/35",
  // The main action on navy surfaces.
  accent:
    "bg-cyan-500 text-navy-950 shadow-[inset_0_1px_0_rgb(255_255_255/0.35),0_6px_18px_-8px_rgb(31_182_232/0.7)] " +
    "hover:bg-cyan-400 focus-visible:ring-cyan-300/40",
  secondary:
    "border border-line bg-white text-navy-900 shadow-[0_1px_2px_rgb(4_24_51/0.06)] " +
    "hover:border-navy-500/45 hover:bg-paper focus-visible:ring-cyan-500/25",
  soft: "bg-ice text-navy-900 hover:bg-[#d9eef8] focus-visible:ring-cyan-500/25",
  ghost: "text-muted hover:bg-navy-900/[0.05] hover:text-navy-900 focus-visible:ring-cyan-500/25",
  "ghost-dark": "text-ice/80 hover:bg-white/10 hover:text-white focus-visible:ring-cyan-300/30",
};

// Every size keeps a 44px touch target on phones; sm only shrinks on wider screens.
const sizes: Record<Size, string> = {
  sm: "min-h-11 rounded-xl px-3.5 text-sm sm:min-h-9",
  md: "min-h-11 rounded-xl px-4.5 text-[15px]",
  lg: "min-h-12 rounded-2xl px-6 text-base",
};

export function buttonClass({
  variant = "primary",
  size = "md",
  block,
  className,
}: {
  variant?: Variant;
  size?: Size;
  block?: boolean;
  className?: string;
}) {
  return clsx(base, variants[variant], sizes[size], block && "w-full", className);
}

type Common = {
  variant?: Variant;
  size?: Size;
  block?: boolean;
  icon?: LucideIcon;
  loading?: boolean;
  children?: ReactNode;
};

export function Button({
  variant,
  size,
  block,
  icon: Icon,
  loading,
  children,
  className,
  disabled,
  type = "button",
  ...rest
}: Common & ComponentProps<"button">) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={buttonClass({ variant, size, block, className })}
      {...rest}
    >
      {loading ? (
        <span aria-hidden className="size-4 shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : (
        Icon && <Icon aria-hidden className="size-4 shrink-0" strokeWidth={2.25} />
      )}
      {children}
    </button>
  );
}

export function ButtonLink({
  variant,
  size,
  block,
  icon: Icon,
  children,
  className,
  ...rest
}: Omit<Common, "loading"> & ComponentProps<typeof Link>) {
  return (
    <Link className={buttonClass({ variant, size, block, className })} {...rest}>
      {Icon && <Icon aria-hidden className="size-4 shrink-0" strokeWidth={2.25} />}
      {children}
    </Link>
  );
}
