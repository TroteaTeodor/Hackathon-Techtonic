import { Skeleton } from "@/components/motion";

/** Rows only: the list page keeps its real title and filters while customers load. */
export function CustomerRowsSkeleton() {
  return (
    <ul aria-busy="true" aria-label="Loading customers" className="flex flex-col gap-2">
      {Array.from({ length: 7 }, (_, i) => (
        <li key={i} className="flex h-[74px] items-center gap-4 rounded-2xl border border-line bg-white px-4">
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-3 w-24" />
          </div>
          <Skeleton className="h-6 w-28 rounded-full" />
          <Skeleton className="hidden h-3 w-20 md:block" />
        </li>
      ))}
    </ul>
  );
}

/** The whole customer list page, used while the session is still being checked. */
export function CustomerListSkeleton() {
  return (
    <div aria-busy="true">
      <Skeleton className="h-9 w-44" />
      <Skeleton className="mt-2.5 h-4 w-64" />
      <div className="mt-5 flex gap-2 overflow-hidden">
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="h-8 w-28 shrink-0 rounded-full" />
        ))}
      </div>
      <div className="mt-5">
        <CustomerRowsSkeleton />
      </div>
    </div>
  );
}

export function CustomerDetailSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading customer">
      <Skeleton className="h-4 w-28" />
      <Skeleton className="mt-4 h-9 w-56" />
      <Skeleton className="mt-2 h-4 w-32" />
      <div className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="flex flex-col gap-5">
          <Skeleton className="h-72 w-full rounded-[var(--radius-card)]" />
          <Skeleton className="h-80 w-full rounded-[var(--radius-card)]" />
        </div>
        <Skeleton className="h-96 w-full rounded-[var(--radius-card)]" />
      </div>
    </div>
  );
}

export function ScaleSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading scale view" className="flex flex-col gap-5">
      <Skeleton className="h-80 w-full rounded-[1.75rem]" />
      <Skeleton className="h-72 w-full rounded-[var(--radius-card)]" />
    </div>
  );
}
