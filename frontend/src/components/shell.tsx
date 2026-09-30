"use client";

import clsx from "clsx";
import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, getMe, logout, USE_MOCKS } from "@/lib/api";
import type { Me, Role } from "@/lib/types";

/** Our own mark: a horizon line with the sun rising over it. Not the KBC logo. */
export function BrandMark({ className, tone = "light" }: { className?: string; tone?: "light" | "dark" }) {
  return (
    <span className={clsx("inline-flex items-center gap-2", className)}>
      <svg viewBox="0 0 28 28" className="size-7" aria-hidden>
        <circle cx="14" cy="16" r="7" fill="#1fb6e8" />
        <rect x="2" y="16" width="24" height="10" fill={tone === "light" ? "#06224a" : "#ffffff"} />
        <path d="M3 16.5h22" stroke={tone === "light" ? "#8fdcf5" : "#06224a"} strokeWidth="2" strokeLinecap="round" />
      </svg>
      <span className={clsx("font-display text-lg font-semibold tracking-tight", tone === "light" ? "text-white" : "text-navy-900")}>
        Foresight
      </span>
    </span>
  );
}

export function LogoutButton({ className }: { className?: string }) {
  const router = useRouter();
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await logout();
        } finally {
          router.replace("/login");
        }
      }}
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-colors",
        className,
      )}
    >
      <LogOut className="size-4" aria-hidden />
      Log out
    </button>
  );
}

/** Loads the session and sends people to the right place. The backend enforces access either way. */
export function useSession(required: Role): Me | null {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  useEffect(() => {
    let active = true;
    getMe()
      .then((user) => {
        if (!active) return;
        if (user.role !== required) router.replace(user.role === "advisor" ? "/advisor" : "/app");
        else setMe(user);
      })
      .catch((err) => {
        if (active && err instanceof ApiError && (err.status === 401 || err.status === 403)) router.replace("/login");
        else if (active) router.replace("/login");
      });
    return () => {
      active = false;
    };
  }, [required, router]);
  return me;
}

export function MockBadge() {
  if (!USE_MOCKS) return null;
  return (
    <span className="rounded-full bg-amber-soft px-2 py-0.5 text-[11px] font-medium text-amber" title="Running on bundled mock data">
      Mock data
    </span>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      role="status"
      aria-label="Loading"
      className={clsx("inline-block size-5 animate-spin rounded-full border-2 border-current border-t-transparent", className)}
    />
  );
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-2xl border border-coral/30 bg-coral-soft p-4 text-sm text-ink">
      <p>{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="mt-2 font-semibold text-coral underline underline-offset-2">
          Try again
        </button>
      )}
    </div>
  );
}

export const errorMessage = (err: unknown) =>
  err instanceof ApiError
    ? err.status === 429
      ? "Too many attempts. Wait a few minutes and try again."
      : err.message
    : "Can't reach Foresight right now. Check your connection and try again.";
