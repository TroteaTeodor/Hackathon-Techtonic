"use client";

import clsx from "clsx";
import { motion } from "motion/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CommandPalette } from "@/components/CommandPalette";
import { CoBrand } from "@/components/Brand";
import { LogoutButton, MockBadge, useSession } from "@/components/shell";
import { CustomerDetailSkeleton, CustomerListSkeleton, ScaleSkeleton } from "@/components/skeletons";

const TABS = [
  { href: "/advisor", label: "Customers" },
  { href: "/advisor/scale", label: "At scale" },
];

export default function AdvisorLayout({ children }: LayoutProps<"/advisor">) {
  const me = useSession("advisor");
  const pathname = usePathname();

  const pending =
    pathname === "/advisor/scale" ? (
      <ScaleSkeleton />
    ) : pathname.startsWith("/advisor/customers/") ? (
      <CustomerDetailSkeleton />
    ) : (
      <CustomerListSkeleton />
    );

  return (
    <div className="flex flex-1 flex-col">
      <header className="sticky top-0 z-20 bg-navy-900 pt-[env(safe-area-inset-top)] text-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <CoBrand href="/advisor" label="Advisor console" />
          </div>
          <div className="flex items-center gap-2">
            <MockBadge />
            {me && <CommandPalette />}
            <LogoutButton className="text-ice/80 hover:bg-white/10 hover:text-white" />
          </div>
        </div>
        <nav className="mx-auto flex max-w-6xl gap-1 px-3 sm:px-5" aria-label="Console">
          {TABS.map((t) => {
            const active = t.href === "/advisor" ? pathname !== "/advisor/scale" : pathname === t.href;
            return (
              <Link
                key={t.href}
                href={t.href}
                aria-current={active ? "page" : undefined}
                className={clsx(
                  "relative px-3 pb-3 pt-1 text-sm font-medium transition-colors",
                  active ? "text-white" : "text-ice/60 hover:text-white",
                )}
              >
                {t.label}
                {active && (
                  <motion.span
                    layoutId="console-tab"
                    className="absolute inset-x-3 bottom-0 h-[3px] rounded-t bg-cyan-500"
                    transition={{ type: "spring", stiffness: 520, damping: 40 }}
                  />
                )}
              </Link>
            );
          })}
        </nav>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 pb-[max(2.5rem,env(safe-area-inset-bottom))] pt-6 sm:px-6">
        {me ? children : pending}
      </main>
    </div>
  );
}
