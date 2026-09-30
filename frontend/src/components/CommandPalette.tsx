"use client";

import { Command } from "cmdk";
import { BarChart3, CornerDownLeft, Search, Users } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { MomentChip } from "@/components/advisor";
import { listCustomers } from "@/lib/api";
import { MOMENTS } from "@/lib/format";
import type { CustomerSummary } from "@/lib/types";

/** Ctrl/⌘ K anywhere in the console: jump to any customer or page by typing a few letters. */
export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [customers, setCustomers] = useState<CustomerSummary[] | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Load the list the first time the palette opens.
  useEffect(() => {
    if (!open || customers) return;
    let live = true;
    listCustomers()
      .then((rows) => live && setCustomers(rows))
      .catch(() => live && setCustomers([]));
    return () => {
      live = false;
    };
  }, [open, customers]);

  const go = (href: string) => {
    setOpen(false);
    router.push(href);
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="hidden min-h-9 items-center gap-2 rounded-xl border border-white/15 bg-white/[0.06] pl-3 pr-2 text-sm text-ice/70 hover:bg-white/[0.12] hover:text-white md:inline-flex"
      >
        <Search aria-hidden className="size-4" />
        Find a customer
        <kbd className="ml-3 rounded-md border border-white/15 px-1.5 py-0.5 font-sans text-[11px] text-ice/60">Ctrl K</kbd>
      </button>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Find a customer"
        className="grid size-10 place-items-center rounded-xl text-ice/80 hover:bg-white/10 md:hidden"
      >
        <Search className="size-5" />
      </button>

      <Command.Dialog
        open={open}
        onOpenChange={setOpen}
        label="Find a customer or page"
        overlayClassName="palette-overlay fixed inset-0 z-50 bg-navy-950/45 backdrop-blur-[3px]"
        contentClassName="palette-panel fixed left-1/2 top-[12vh] z-50 w-[min(36rem,calc(100vw-2rem))] -translate-x-1/2 overflow-hidden rounded-3xl bg-white shadow-[0_40px_90px_-30px_rgb(4_24_51/0.7)]"
      >
        <div className="flex items-center gap-3 border-b border-line px-5">
          <Search aria-hidden className="size-5 shrink-0 text-muted" />
          <Command.Input
            autoFocus
            placeholder="Search customers, moments or pages"
            className="h-14 w-full bg-transparent text-base text-ink outline-none placeholder:text-muted"
          />
          <kbd className="rounded-md border border-line px-1.5 py-0.5 text-[11px] text-muted">Esc</kbd>
        </div>
        <Command.List data-lenis-prevent className="thin-scroll max-h-[min(60vh,26rem)] overflow-y-auto overscroll-contain p-2">
          <Command.Empty className="px-4 py-10 text-center text-sm text-muted">
            No one matches that. Try a first name or a moment, like “moving”.
          </Command.Empty>

          <Command.Group heading="Pages" className="palette-group">
            <Item onSelect={() => go("/advisor")} icon={<Users className="size-4" />} label="All customers" hint="List" />
            <Item onSelect={() => go("/advisor/scale")} icon={<BarChart3 className="size-4" />} label="At scale" hint="2.3M projection" />
          </Command.Group>

          <Command.Group heading={customers ? `Customers (${customers.length})` : "Customers"} className="palette-group">
            {!customers && <p className="px-3 py-3 text-sm text-muted">Loading customers…</p>}
            {customers?.map((c) => (
              <Command.Item
                key={c.id}
                value={`${c.name} ${c.city} ${c.moment_key ? MOMENTS[c.moment_key].label : ""}`}
                onSelect={() => go(`/advisor/customers/${c.id}`)}
                className="palette-item"
              >
                <span className="grid size-8 shrink-0 place-items-center rounded-full bg-ice text-xs font-semibold text-navy-700">
                  {c.name
                    .split(" ")
                    .map((p) => p[0])
                    .slice(0, 2)
                    .join("")}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-semibold text-navy-900">{c.name}</span>
                  <span className="block truncate text-xs text-muted">
                    {c.age}, {c.city}
                    {c.review_count > 0 && <span className="text-amber"> · {c.review_count} to review</span>}
                  </span>
                </span>
                <MomentChip moment={c.moment_key} confidence={c.moment_confidence} />
              </Command.Item>
            ))}
          </Command.Group>
        </Command.List>
        <div className="flex items-center justify-between border-t border-line bg-paper px-5 py-2.5 text-xs text-muted">
          <span>↑ ↓ to move</span>
          <span className="inline-flex items-center gap-1">
            <CornerDownLeft className="size-3.5" /> to open
          </span>
        </div>
      </Command.Dialog>
    </>
  );
}

function Item({ onSelect, icon, label, hint }: { onSelect: () => void; icon: React.ReactNode; label: string; hint: string }) {
  return (
    <Command.Item onSelect={onSelect} value={label} className="palette-item">
      <span className="grid size-8 shrink-0 place-items-center rounded-full bg-navy-900 text-white">{icon}</span>
      <span className="flex-1 font-semibold text-navy-900">{label}</span>
      <span className="text-xs text-muted">{hint}</span>
    </Command.Item>
  );
}
