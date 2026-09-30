"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/Button";
import { BrandMark, MockBadge } from "@/components/shell";
import { ApiError, login, USE_MOCKS } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const me = await login(username.trim(), password);
      router.replace(me.role === "advisor" ? "/advisor" : "/app");
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 429
          ? "Too many attempts. Wait a few minutes and try again."
          : err instanceof ApiError
            ? "That username and password don't match. Check them and try again."
            : "Can't reach Foresight right now. Check your connection and try again.",
      );
      setBusy(false);
    }
  }

  return (
    <main className="flex flex-1 flex-col bg-navy-900 lg:flex-row">
      <section className="relative isolate flex min-h-[38svh] flex-col justify-between overflow-hidden px-6 pb-8 pt-[max(1.5rem,env(safe-area-inset-top))] lg:min-h-svh lg:flex-1 lg:p-12">
        <div
          aria-hidden
          className="absolute inset-0 -z-10 bg-cover bg-center opacity-70"
          style={{ backgroundImage: "url(/moments/login_hero.webp)" }}
        />
        <div className="absolute inset-0 -z-10 bg-gradient-to-t from-navy-900 via-navy-900/40 to-navy-900/10" />
        <div className="flex items-center justify-between">
          <BrandMark />
          <MockBadge />
        </div>
        <div className="max-w-md">
          <h1 className="font-display text-[2.1rem] font-semibold leading-[1.05] tracking-tight text-white sm:text-5xl">
            See the next twelve months before they happen.
          </h1>
          <p className="mt-3 max-w-sm text-[15px] leading-relaxed text-ice/75">
            Foresight notices the big moments in your life and helps before money gets tight.
          </p>
        </div>
      </section>

      <section className="flex flex-1 flex-col justify-center rounded-t-[1.75rem] bg-paper px-6 pb-[max(2rem,env(safe-area-inset-bottom))] pt-8 lg:max-w-xl lg:rounded-none lg:px-16">
        <form onSubmit={onSubmit} className="mx-auto w-full max-w-sm" noValidate>
          <h2 className="font-display text-2xl font-semibold tracking-tight text-navy-900">Log in</h2>
          <label className="mt-6 block text-sm font-medium text-ink" htmlFor="username">
            Username
          </label>
          <input
            id="username"
            name="username"
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="mt-1.5 w-full rounded-xl border border-line bg-white px-4 py-3 text-base outline-none transition focus:border-cyan-500 focus:ring-4 focus:ring-cyan-500/15"
          />
          <label className="mt-4 block text-sm font-medium text-ink" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1.5 w-full rounded-xl border border-line bg-white px-4 py-3 text-base outline-none transition focus:border-cyan-500 focus:ring-4 focus:ring-cyan-500/15"
          />
          {error && (
            <p role="alert" className="mt-4 rounded-xl bg-coral-soft px-4 py-3 text-sm text-ink">
              {error}
            </p>
          )}
          <Button type="submit" size="lg" block loading={busy} disabled={!username || !password} className="mt-6">
            {busy ? "Logging in…" : "Log in"}
          </Button>
          <p className="mt-5 text-sm leading-relaxed text-muted">
            Demo accounts: <span className="font-medium text-ink">sara</span>,{" "}
            <span className="font-medium text-ink">julie</span> or <span className="font-medium text-ink">jan</span> for
            the customer app, <span className="font-medium text-ink">advisor</span> for the console.
            {USE_MOCKS && " In mock mode any password works."}
          </p>
        </form>
      </section>
    </main>
  );
}
