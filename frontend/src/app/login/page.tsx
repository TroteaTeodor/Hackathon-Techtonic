"use client";

import { MeshGradient } from "@paper-design/shaders-react";
import clsx from "clsx";
import { ArrowRight, Check, Eye, EyeOff } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Button } from "@/components/Button";
import { SmoothField } from "@/components/SmoothField";
import { BrandMark, MockBadge } from "@/components/shell";
import { ApiError, login, USE_MOCKS } from "@/lib/api";

const MOMENT_LINES = [
  "before you move.",
  "before the baby.",
  "before a new job.",
  "before you retire.",
  "before it gets tight.",
];

const DEMO_ACCOUNTS = [
  { username: "sara", who: "Sara", what: "Moving home" },
  { username: "julie", who: "Julie", what: "Money is tight" },
  { username: "jan", who: "Jan", what: "Routine" },
  { username: "advisor", who: "Advisor", what: "Console" },
];

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [busy, setBusy] = useState(false);
  const [welcome, setWelcome] = useState<string | null>(null);
  const passwordRef = useRef<HTMLInputElement | null>(null);
  const typingTimer = useRef<number | null>(null);

  useEffect(() => () => {
    if (typingTimer.current) window.clearTimeout(typingTimer.current);
  }, []);

  /** Types a demo username into the field, letter by letter, then hands focus to the password. */
  function fillDemo(name: string) {
    if (typingTimer.current) window.clearTimeout(typingTimer.current);
    setError(null);
    setUsername("");
    if (USE_MOCKS) setPassword("demo");
    let i = 0;
    const step = () => {
      i += 1;
      setUsername(name.slice(0, i));
      if (i < name.length) typingTimer.current = window.setTimeout(step, 55);
      else passwordRef.current?.focus();
    };
    typingTimer.current = window.setTimeout(step, 120);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError("Enter your username and password.");
      setAttempt((a) => a + 1);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const me = await login(username.trim(), password);
      setWelcome(me.display_name.split(" ")[0]);
      window.setTimeout(() => router.replace(me.role === "advisor" ? "/advisor" : "/app"), 650);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 429
          ? "Too many attempts. Wait a few minutes and try again."
          : err instanceof ApiError
            ? "That username and password don't match. Check them and try again."
            : "Can't reach Foresight right now. Check your connection and try again.",
      );
      setAttempt((a) => a + 1);
      setBusy(false);
    }
  }

  return (
    <main className="flex flex-1 flex-col bg-navy-950 lg:flex-row">
      {/* ---- Story side: a living gradient, the promise typed out, and a glimpse of the product ---- */}
      <section className="relative isolate flex min-h-[44svh] flex-col justify-between overflow-hidden px-6 pb-12 pt-[max(1.5rem,env(safe-area-inset-top))] lg:min-h-svh lg:flex-1 lg:px-14 lg:py-12">
        <FluidBackdrop />

        <div className="flex items-center justify-between">
          <BrandMark href={null} />
          <MockBadge />
        </div>

        <div className="relative max-w-[46rem]">
          <h1 className="font-display text-[2.15rem] font-semibold leading-[1.04] tracking-[-0.03em] text-white sm:text-5xl lg:text-[3.35rem] xl:text-[3.6rem]">
            See the next twelve months
            <br />
            <Typewriter lines={MOMENT_LINES} className="text-cyan-300" />
          </h1>
          <p className="mt-4 max-w-md text-[15px] leading-relaxed text-ice/75 sm:text-base">
            Foresight notices the big moments in your life from how you bank, and helps before money gets tight. Never
            with a sales pitch when things are hard.
          </p>
        </div>

        <ForecastPreview />
      </section>

      {/* ---- Form side ---- */}
      <section className="relative z-10 -mt-7 flex flex-1 flex-col justify-center rounded-t-[1.75rem] bg-paper px-6 pb-[max(2rem,env(safe-area-inset-bottom))] pt-9 lg:mt-0 lg:max-w-[34rem] lg:rounded-none lg:px-16">
        <form
          key={attempt}
          onSubmit={onSubmit}
          className={clsx("mx-auto w-full max-w-sm", attempt > 0 && error && "shake")}
          noValidate
        >
          <h2 className="font-display text-[1.7rem] font-semibold tracking-tight text-navy-900">Welcome back</h2>
          <p className="mt-1 text-[15px] text-muted">Log in to see what’s coming up.</p>

          <SmoothField
            className="mt-7"
            label="Username"
            name="username"
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            enterKeyHint="next"
            value={username}
            onValueChange={(v) => {
              setUsername(v);
              setError(null);
            }}
            invalid={!!error}
          />

          <SmoothField
            className="mt-3"
            label="Password"
            name="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            enterKeyHint="go"
            masked={!showPassword}
            value={password}
            inputRef={passwordRef}
            onValueChange={(v) => {
              setPassword(v);
              setError(null);
            }}
            onKeyUp={(e) => setCapsLock(e.getModifierState("CapsLock"))}
            invalid={!!error}
            trailing={
              <button
                type="button"
                onClick={() => {
                  setShowPassword((s) => !s);
                  passwordRef.current?.focus();
                }}
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
                className="grid size-11 place-items-center rounded-xl text-muted hover:bg-paper hover:text-navy-900"
              >
                {showPassword ? <EyeOff className="size-[18px]" /> : <Eye className="size-[18px]" />}
              </button>
            }
            hint={capsLock ? <span className="text-amber">Caps Lock is on.</span> : null}
          />

          <div aria-live="polite">
            {error && (
              <p role="alert" className="fade-up mt-4 rounded-xl bg-coral-soft px-4 py-3 text-sm text-ink">
                {error}
              </p>
            )}
          </div>

          <Button
            type="submit"
            size="lg"
            block
            loading={busy && !welcome}
            className={clsx("group mt-6", welcome && "bg-mint! hover:bg-mint!")}
            icon={welcome ? Check : undefined}
          >
            {welcome ? `Welcome, ${welcome}` : busy ? "Logging in…" : (
              <>
                Log in <ArrowRight aria-hidden className="size-4 transition-transform duration-300 group-hover:translate-x-0.5" />
              </>
            )}
          </Button>

          <div className="mt-8">
            <p className="text-sm font-medium text-ink">Try a demo account</p>
            <div className="mt-2.5 grid grid-cols-2 gap-2">
              {DEMO_ACCOUNTS.map((d) => (
                <button
                  key={d.username}
                  type="button"
                  onClick={() => fillDemo(d.username)}
                  className={clsx(
                    "group flex min-h-12 items-center gap-2.5 rounded-xl border px-3 text-left transition-[border-color,background-color,box-shadow]",
                    username === d.username
                      ? "border-cyan-500 bg-ice shadow-[0_0_0_3px_rgb(31_182_232/0.15)]"
                      : "border-line bg-white hover:border-navy-500/40",
                  )}
                >
                  <span
                    className={clsx(
                      "grid size-7 shrink-0 place-items-center rounded-full text-xs font-semibold",
                      d.username === "advisor" ? "bg-navy-900 text-white" : "bg-ice text-navy-700",
                    )}
                  >
                    {d.who[0]}
                  </span>
                  <span className="min-w-0 leading-tight">
                    <span className="block text-sm font-semibold text-navy-900">{d.who}</span>
                    <span className="block truncate text-xs text-muted">{d.what}</span>
                  </span>
                </button>
              ))}
            </div>
            <p className="mt-3 text-xs leading-relaxed text-muted">
              {USE_MOCKS
                ? "Mock mode: any password works."
                : "Demo accounts share one password, set by the team running this demo."}
            </p>
          </div>
        </form>
      </section>
    </main>
  );
}

/** Slow, living gradient in the brand's navy and cyan, with the city photo breathing through. */
function FluidBackdrop() {
  const [reduced] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  return (
    <div aria-hidden className="absolute inset-0 -z-10">
      <MeshGradient
        colors={["#041833", "#0b3a73", "#1fb6e8", "#06224a", "#3d6194"]}
        distortion={0.85}
        swirl={0.35}
        grainOverlay={0.06}
        speed={reduced ? 0 : 0.22}
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
      />
      <div
        className="absolute inset-0 bg-cover bg-center opacity-25 mix-blend-soft-light"
        style={{ backgroundImage: "url(/moments/login_hero.webp)" }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-navy-950/85 via-navy-950/20 to-transparent" />
    </div>
  );
}

/** Types a line, holds it, erases it and moves to the next, with a soft caret. */
function Typewriter({ lines, className }: { lines: string[]; className?: string }) {
  const [text, setText] = useState("");
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      const t = window.setTimeout(() => setText(lines[0]), 0);
      return () => window.clearTimeout(t);
    }
    let line = 0;
    let len = 0;
    let deleting = false;
    let timer = 0;
    const tick = () => {
      const target = lines[line];
      if (!deleting) {
        len += 1;
        setText(target.slice(0, len));
        if (len === target.length) {
          deleting = true;
          timer = window.setTimeout(tick, 2200);
          return;
        }
        timer = window.setTimeout(tick, 38 + Math.random() * 45);
      } else {
        len -= 1;
        setText(target.slice(0, len));
        if (len === 0) {
          deleting = false;
          line = (line + 1) % lines.length;
          timer = window.setTimeout(tick, 280);
          return;
        }
        timer = window.setTimeout(tick, 18);
      }
    };
    timer = window.setTimeout(tick, 500);
    return () => window.clearTimeout(timer);
  }, [lines]);

  // The longest line sits invisibly in the same grid cell, so the heading keeps its height
  // whatever is typed and nothing below it moves.
  const longest = lines.reduce((a, b) => (b.length > a.length ? b : a), "");
  return (
    <span className={clsx("inline-grid align-top", className)}>
      <span className="sr-only">{lines[0]}</span>
      <span aria-hidden className="invisible col-start-1 row-start-1">
        {longest}
        <span className="ml-1 inline-block w-[3px]" />
      </span>
      <span aria-hidden className="col-start-1 row-start-1">
        {text}
        <span className="caret-blink ml-1 inline-block h-[0.85em] w-[3px] translate-y-[0.08em] rounded-full bg-cyan-300 align-baseline" />
      </span>
    </span>
  );
}

/** A small, honest preview of what Foresight shows: a forecast that dips, and the heads-up that comes with it. */
function ForecastPreview() {
  return (
    <div
      aria-hidden
      className="float-y relative mt-8 hidden w-full max-w-sm self-start rounded-3xl border border-white/15 bg-white/[0.08] p-4 text-white shadow-[0_30px_60px_-30px_rgb(0_0_0/0.6)] backdrop-blur-md sm:block lg:max-w-md"
    >
      <div className="flex items-center justify-between text-xs text-ice/70">
        <span>Sara’s next 12 months</span>
        <span className="rounded-full bg-coral/20 px-2 py-0.5 font-medium text-[#ffb59e]">November looks tight</span>
      </div>
      <svg viewBox="0 0 320 90" className="mt-3 h-auto w-full overflow-visible">
        <defs>
          <linearGradient id="pv-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="rgb(76 198 238 / 0.35)" />
            <stop offset="100%" stopColor="rgb(76 198 238 / 0)" />
          </linearGradient>
        </defs>
        <line x1="0" x2="320" y1="70" y2="70" stroke="rgb(234 246 252 / 0.35)" strokeDasharray="4 5" />
        <path
          d="M0,22 C18,20 30,18 42,20 C56,24 58,76 70,78 C84,80 100,66 124,62 C150,58 170,56 190,42 C212,28 240,30 262,26 C284,22 300,20 320,16 L320,90 L0,90 Z"
          fill="url(#pv-fill)"
        />
        <path
          className="preview-line"
          pathLength={1}
          d="M0,22 C18,20 30,18 42,20 C56,24 58,76 70,78 C84,80 100,66 124,62 C150,58 170,56 190,42 C212,28 240,30 262,26 C284,22 300,20 320,16"
          fill="none"
          stroke="#4cc6ee"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <circle cx="70" cy="78" r="5" fill="#e4572e" stroke="#06224a" strokeWidth="2" className="preview-dot" />
      </svg>
      <div className="mt-2 rounded-2xl bg-white/[0.08] px-3 py-2.5 text-[13px] leading-snug text-ice/90">
        <span className="font-semibold text-white">Heads-up for November.</span> Notary fees take you to −€155. Move €500
        from savings now, in one tap.
      </div>
    </div>
  );
}
