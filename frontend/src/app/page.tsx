"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { BrandMark, Spinner } from "@/components/shell";
import { getMe } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    getMe()
      .then((me) => router.replace(me.role === "advisor" ? "/advisor" : "/app"))
      .catch(() => router.replace("/login"));
  }, [router]);

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 bg-navy-900">
      <BrandMark />
      <Spinner className="text-cyan-400" />
    </main>
  );
}
