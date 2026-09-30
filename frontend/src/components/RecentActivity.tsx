"use client";

import clsx from "clsx";
import {
  Baby,
  Briefcase,
  Car,
  ChevronDown,
  CreditCard,
  FileSignature,
  Fuel,
  House,
  Landmark,
  PiggyBank,
  Plane,
  ReceiptText,
  Repeat,
  Ticket,
  Tv,
  ShieldCheck,
  ShoppingBasket,
  Smartphone,
  TrainFront,
  TriangleAlert,
  Utensils,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Skeleton } from "@/components/motion";
import { getTransactions } from "@/lib/api";
import { signedMoney } from "@/lib/format";
import type { Signal, TransactionCategory } from "@/lib/types";

const CATEGORIES: [RegExp, LucideIcon, string][] = [
  [/salary|wage|payroll|holiday pay/i, Briefcase, "bg-mint-soft text-mint"],
  [/returned|missed|overdraft|collection|reminder fee|insufficient/i, TriangleAlert, "bg-coral-soft text-coral"],
  [/rent|mortgage|landlord|immo/i, House, "bg-ice text-navy-700"],
  [/notary|notaris/i, FileSignature, "bg-ice text-navy-700"],
  [/grocer|colruyt|delhaize|aldi|lidl|carrefour|albert heijn/i, ShoppingBasket, "bg-ice text-navy-700"],
  [/energy|engie|fluvius|luminus|electric|gas|water/i, Zap, "bg-ice text-navy-700"],
  [/telecom|proximus|telenet|orange|base|mobile/i, Smartphone, "bg-ice text-navy-700"],
  [/nmbs|sncb|de lijn|stib|train|transport/i, TrainFront, "bg-ice text-navy-700"],
  [/fuel|totalenergies|shell|q8|esso/i, Fuel, "bg-ice text-navy-700"],
  [/\bcars?\b|dealer|toyota|garage/i, Car, "bg-ice text-navy-700"],
  [/baby|dreambaby|pharmacy/i, Baby, "bg-ice text-navy-700"],
  [/flight|airline|brussels airlines|ryanair|hotel|booking/i, Plane, "bg-ice text-navy-700"],
  [/insurance|ethias|ag insurance|premium/i, ShieldCheck, "bg-ice text-navy-700"],
  [/restaurant|café|cafe|deliveroo|takeaway|uber eats/i, Utensils, "bg-ice text-navy-700"],
  [/card|bancontact|visa|mastercard/i, CreditCard, "bg-ice text-navy-700"],
  [/kbc|bank|transfer|savings/i, Landmark, "bg-ice text-navy-700"],
];

// The backend classifies every transaction; the regexes above are only a fallback for older data.
const BY_CATEGORY: Record<TransactionCategory, [LucideIcon, string, string]> = {
  income: [Briefcase, "bg-mint-soft text-mint", "Income"],
  housing: [House, "bg-ice text-navy-700", "Housing"],
  energy: [Zap, "bg-ice text-navy-700", "Energy & water"],
  telecom: [Smartphone, "bg-ice text-navy-700", "Phone & internet"],
  groceries: [ShoppingBasket, "bg-ice text-navy-700", "Groceries"],
  transport: [TrainFront, "bg-ice text-navy-700", "Transport"],
  subscriptions: [Tv, "bg-ice text-navy-700", "Subscription"],
  entertainment: [Ticket, "bg-ice text-navy-700", "Entertainment"],
  dining: [Utensils, "bg-ice text-navy-700", "Eating out"],
  shopping: [CreditCard, "bg-ice text-navy-700", "Shopping"],
  health: [Baby, "bg-ice text-navy-700", "Health"],
  insurance: [ShieldCheck, "bg-ice text-navy-700", "Insurance"],
  travel: [Plane, "bg-ice text-navy-700", "Travel"],
  family: [Baby, "bg-ice text-navy-700", "Family & children"],
  loans: [Landmark, "bg-ice text-navy-700", "Loans & credit"],
  fees: [TriangleAlert, "bg-coral-soft text-coral", "Bank fees & interest"],
  savings: [PiggyBank, "bg-ice text-navy-700", "Savings"],
  other: [ReceiptText, "bg-ice text-navy-700", "Other"],
};

function categorize(t: Signal) {
  if (t.category) {
    const [icon, tone, label] = BY_CATEGORY[t.category];
    return { icon, tone, label };
  }
  for (const [re, icon, tone] of CATEGORIES) if (re.test(t.description)) return { icon, tone, label: null };
  return { icon: ReceiptText, tone: "bg-ice text-navy-700", label: null };
}

/** "Groceries — Aldi" reads best as the merchant on top and the category underneath. */
function split(description: string) {
  const [what, who] = description.split(/\s+[—–-]\s+/, 2);
  return who ? { title: who, sub: what } : { title: description, sub: null };
}

function dayLabel(date: string, today: Date) {
  const d = new Date(`${date}T00:00:00`);
  const t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const diff = Math.round((t.getTime() - d.getTime()) / 86_400_000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
}

/** The customer's own statement: recent transactions grouped by day, newest first. */
export function RecentActivity() {
  const [rows, setRows] = useState<Signal[] | null | undefined>(undefined);
  const [failed, setFailed] = useState(false);
  const [all, setAll] = useState(false);

  useEffect(() => {
    let live = true;
    getTransactions(40)
      .then((r) => live && setRows(r))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, []);

  // No endpoint yet (older backend): leave the section out rather than show an error.
  if (rows === null) return null;

  const visible = rows ? (all ? rows : rows.slice(0, 6)) : [];
  const today = new Date();
  const groups: { label: string; items: Signal[] }[] = [];
  for (const r of visible) {
    const label = dayLabel(r.date, today);
    const last = groups.at(-1);
    if (last?.label === label) last.items.push(r);
    else groups.push({ label, items: [r] });
  }

  return (
    <section aria-labelledby="activity">
      <div className="flex items-baseline justify-between px-1">
        <h2 id="activity" className="font-display text-xl font-semibold tracking-tight text-navy-900">
          Recent activity
        </h2>
        {rows && rows.length > 0 && <span className="text-sm text-muted">Current account</span>}
      </div>

      <div className="elev-1 mt-3 overflow-hidden rounded-[var(--radius-card)] bg-white">
        {rows === undefined && !failed && (
          <ul aria-busy="true" aria-label="Loading transactions">
            {Array.from({ length: 4 }, (_, i) => (
              <li key={i} className="flex items-center gap-3 border-b border-line px-4 py-3.5 last:border-0">
                <Skeleton className="size-10 rounded-full" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-20" />
                </div>
                <Skeleton className="h-4 w-16" />
              </li>
            ))}
          </ul>
        )}

        {failed && <p className="px-4 py-6 text-sm text-muted">Your transactions couldn’t load. Pull down or reopen the app to try again.</p>}

        {rows && rows.length === 0 && <p className="px-4 py-6 text-sm text-muted">No transactions yet.</p>}

        {groups.map((g) => (
          <div key={g.label}>
            <p className="bg-paper/70 px-4 pb-1.5 pt-3 text-xs font-medium text-muted">{g.label}</p>
            <ul>
              {g.items.map((t) => {
                const { icon: Icon, tone, label } = categorize(t);
                const { title, sub } = split(t.description);
                const amount = t.amount ?? 0;
                return (
                  <li key={t.id} className="flex items-center gap-3 px-4 py-3">
                    <span className={clsx("grid size-10 shrink-0 place-items-center rounded-full", tone)}>
                      <Icon aria-hidden className="size-[18px]" strokeWidth={2} />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium text-ink">{title}</span>
                      <span className="flex items-center gap-1.5 truncate text-[13px] text-muted">
                        {label ?? sub}
                        {t.recurring && (
                          <span className="inline-flex items-center gap-0.5 rounded-full bg-ice px-1.5 py-px text-[11px] font-medium text-navy-700">
                            <Repeat aria-hidden className="size-3" /> recurring
                          </span>
                        )}
                      </span>
                    </span>
                    <span className={clsx("tabular shrink-0 font-semibold", amount > 0 ? "text-mint" : "text-ink")}>
                      {signedMoney(amount)}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}

        {rows && rows.length > 6 && (
          <button
            type="button"
            onClick={() => setAll((v) => !v)}
            aria-expanded={all}
            className="flex min-h-12 w-full items-center justify-center gap-1.5 border-t border-line text-sm font-semibold text-navy-700 hover:bg-paper"
          >
            {all ? "Show less" : `Show all ${rows.length}`}
            <ChevronDown aria-hidden className={clsx("size-4 transition-transform", all && "rotate-180")} />
          </button>
        )}
      </div>
    </section>
  );
}
