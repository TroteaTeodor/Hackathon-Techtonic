"use client";

import clsx from "clsx";
import { LogOut, RotateCw } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/Button";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, getMe, logout, USE_MOCKS } from "@/lib/api";
import type { Me, Role } from "@/lib/types";

/** Our own mark: a horizon line with the sun rising over it. Not the KBC logo. Links home. */
export function BrandMark({
  className,
  tone = "light",
  href = "/",
}: {
  className?: string;
  tone?: "light" | "dark";
  href?: string | null;
}) {
  const mark = (
    <>
      <svg viewBox="0 0 28 28" className="size-7 transition-transform duration-500 group-hover:-translate-y-0.5" aria-hidden>
        <circle cx="14" cy="16" r="7" fill="#1fb6e8" />
        <rect x="2" y="16" width="24" height="10" fill={tone === "light" ? "#06224a" : "#ffffff"} />
        <path d="M3 16.5h22" stroke={tone === "light" ? "#8fdcf5" : "#06224a"} strokeWidth="2" strokeLinecap="round" />
      </svg>
      <span className={clsx("font-display text-lg font-semibold tracking-tight", tone === "light" ? "text-white" : "text-navy-900")}>
        Foresight
      </span>
    </>
  );
  if (!href) return <span className={clsx("inline-flex items-center gap-2", className)}>{mark}</span>;
  return (
    <Link href={href} aria-label="Foresight home" className={clsx("press group -m-1.5 inline-flex items-center gap-2 rounded-xl p-1.5", className)}>
      {mark}
    </Link>
  );
}

export function LogoutButton({ className }: { className?: string }) {
  const router = useRouter();
  return (
    <Button
      variant="ghost-dark"
      size="sm"
      icon={LogOut}
      className={className}
      onClick={async () => {
        try {
          await logout();
        } finally {
          router.replace("/login");
        }
      }}
    >
      Log out
    </Button>
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
        <Button variant="secondary" size="sm" icon={RotateCw} onClick={onRetry} className="mt-3">
          Try again
        </Button>
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
