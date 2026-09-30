// Typed client for the frozen API contract (openspec/changes/kbc-foresight/design.md).
// With NEXT_PUBLIC_USE_MOCKS=true every call is answered from src/mocks/ after 300 ms.

import type {
  CustomerDetail,
  CustomerOverview,
  CustomerSummary,
  Intervention,
  Me,
  MomentKey,
  Proactivity,
  ScaleStats,
  Signal,
  SignalCreate,
} from "./types";

import afterInjectFixture from "@/mocks/customer-detail-after-inject.json";
import janFixture from "@/mocks/customer-detail-jan.json";
import saraDetailFixture from "@/mocks/customer-detail-sara.json";
import customersFixture from "@/mocks/customers.json";
import meAdvisorFixture from "@/mocks/me-advisor.json";
import meCustomerFixture from "@/mocks/me-customer.json";
import overviewFixture from "@/mocks/overview-sara.json";
import scaleFixture from "@/mocks/scale.json";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: init.method ?? "GET",
    credentials: "include",
    headers: init.body === undefined ? undefined : { "Content-Type": "application/json" },
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") detail = data.detail;
    } catch {
      // Non-JSON error body; keep the status text.
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---------------------------------------------------------------------------
// Mock mode: an in-memory copy of the fixtures, so actions visibly change state.

const clone = <T>(value: T): T => structuredClone(value);
const delay = <T>(value: T): Promise<T> =>
  new Promise((resolve) => setTimeout(() => resolve(clone(value)), 300));

const MOCK_ROLE_KEY = "foresight.mock-role";

function mockRole(): Me["role"] | null {
  try {
    const role = sessionStorage.getItem(MOCK_ROLE_KEY);
    return role === "customer" || role === "advisor" ? role : null;
  } catch {
    return null;
  }
}

const mock = {
  overview: clone(overviewFixture) as CustomerOverview,
  overviewAll: clone(overviewFixture.interventions) as Intervention[],
  details: new Map<number, CustomerDetail>([
    [1, clone(saraDetailFixture) as CustomerDetail],
    [7, clone(janFixture) as CustomerDetail],
  ]),
  customers: clone(customersFixture) as CustomerSummary[],
};

const MOMENT_LABELS: Record<MomentKey, string> = {
  moving_home: "Moving home",
  growing_family: "Growing family",
  new_job: "New job",
  approaching_retirement: "Approaching retirement",
  buying_car: "Buying a car",
  travel_abroad: "Travel abroad",
  financial_stress: "Financial stress",
  no_clear_moment: "No clear moment",
};

// Customers without their own fixture reuse Sara's detail, relabelled from the list row.
function mockDetail(id: number): CustomerDetail {
  const existing = mock.details.get(id);
  if (existing) return existing;
  const row = mock.customers.find((c) => c.id === id);
  if (!row) throw new ApiError(404, "Customer not found");
  const base = clone(saraDetailFixture) as CustomerDetail;
  const [first_name, ...rest] = row.name.split(" ");
  base.customer = { ...base.customer, id, first_name, last_name: rest.join(" "), age: row.age, city: row.city };
  if (base.moment && row.moment_key) {
    const key = row.moment_key;
    const confidence = row.moment_confidence ?? 0.5;
    const others = (Object.keys(MOMENT_LABELS) as MomentKey[]).filter((k) => k !== key);
    const share = (1 - confidence) / others.length;
    base.moment = {
      ...base.moment,
      key,
      label: MOMENT_LABELS[key],
      confidence,
      stress: row.stress ?? 0,
      probabilities: Object.fromEntries([
        [key, confidence],
        ...others.map((k) => [k, Math.round(share * 1000) / 1000]),
      ]) as Record<MomentKey, number>,
      rationale: "Mock data: detail reused from the Sara fixture for this customer.",
    };
  }
  base.interventions = base.interventions.map((i) => ({ ...i, id: id * 100 + (i.id % 100) }));
  mock.details.set(id, base);
  return base;
}

function isSalesCard(i: Intervention) {
  return i.line !== "support" && !i.key.startsWith("pinch_point");
}

function syncSummary(detail: CustomerDetail) {
  const row = mock.customers.find((c) => c.id === detail.customer.id);
  if (!row) return;
  row.moment_key = detail.moment?.key ?? null;
  row.moment_confidence = detail.moment?.confidence ?? null;
  row.stress = detail.moment?.stress ?? null;
  row.next_pinch_month = detail.twin.pinch_points[0]?.month ?? null;
  row.review_count = detail.interventions.filter((i) => i.status === "review").length;
}

// ---------------------------------------------------------------------------
// Auth

export async function login(username: string, password: string): Promise<Me> {
  if (USE_MOCKS) {
    if (!username.trim() || !password) throw new ApiError(401, "Invalid username or password");
    const me = (username.trim().toLowerCase() === "advisor" ? meAdvisorFixture : meCustomerFixture) as Me;
    try {
      sessionStorage.setItem(MOCK_ROLE_KEY, me.role);
    } catch {
      // Storage unavailable; the mock session lasts for this page only.
    }
    return delay(me);
  }
  return request<Me>("/auth/login", { method: "POST", body: { username, password } });
}

export async function logout(): Promise<void> {
  if (USE_MOCKS) {
    try {
      sessionStorage.removeItem(MOCK_ROLE_KEY);
    } catch {
      // Nothing to clear.
    }
    return;
  }
  await request<void>("/auth/logout", { method: "POST" });
}

export async function getMe(): Promise<Me> {
  if (USE_MOCKS) {
    const role = mockRole();
    if (!role) throw new ApiError(401, "Not authenticated");
    return delay((role === "advisor" ? meAdvisorFixture : meCustomerFixture) as Me);
  }
  return request<Me>("/auth/me");
}

// ---------------------------------------------------------------------------
// Customer

export async function getOverview(): Promise<CustomerOverview> {
  if (USE_MOCKS) return delay(mock.overview);
  return request<CustomerOverview>("/me/overview");
}

/**
 * The customer's own recent transactions, newest first. Resolves to null when the backend has no
 * such endpoint yet, so the app can simply leave the section out.
 */
export async function getTransactions(limit = 40): Promise<Signal[] | null> {
  if (USE_MOCKS) {
    return delay((saraDetailFixture.signals as Signal[]).filter((s) => s.kind === "transaction").slice(0, limit));
  }
  try {
    return await request<Signal[]>(`/me/transactions?limit=${limit}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export async function setProactivity(proactivity: Proactivity): Promise<CustomerOverview> {
  if (USE_MOCKS) {
    mock.overview.customer.proactivity = proactivity;
    mock.overview.interventions = mock.overviewAll.filter(
      (i) => i.feedback !== "not_relevant" && (proactivity !== "minimal" || !isSalesCard(i)),
    );
    return delay(mock.overview);
  }
  return request<CustomerOverview>("/me/preferences", { method: "PUT", body: { proactivity } });
}

export async function rejectMoment(): Promise<CustomerOverview> {
  if (USE_MOCKS) {
    const m = mock.overview.moment;
    if (m) {
      mock.overview.moment = {
        ...m,
        key: "no_clear_moment",
        label: MOMENT_LABELS.no_clear_moment,
        source: "customer",
        analyzed_at: new Date().toISOString(),
      };
    }
    return delay(mock.overview);
  }
  return request<CustomerOverview>("/me/moment/reject", { method: "POST" });
}

export async function sendFeedback(
  interventionId: number,
  feedback: "helpful" | "not_relevant",
): Promise<CustomerOverview> {
  if (USE_MOCKS) {
    const card = mock.overviewAll.find((i) => i.id === interventionId);
    if (!card) throw new ApiError(404, "Intervention not found");
    card.feedback = feedback;
    mock.overview.interventions = mock.overview.interventions
      .map((i) => (i.id === interventionId ? { ...i, feedback } : i))
      .filter((i) => i.feedback !== "not_relevant");
    return delay(mock.overview);
  }
  return request<CustomerOverview>(`/me/interventions/${interventionId}/feedback`, {
    method: "POST",
    body: { feedback },
  });
}

// ---------------------------------------------------------------------------
// Advisor

export async function listCustomers(
  filters: { moment?: MomentKey | ""; needsReview?: boolean } = {},
): Promise<CustomerSummary[]> {
  if (USE_MOCKS) {
    return delay(
      mock.customers.filter(
        (c) =>
          (!filters.moment || c.moment_key === filters.moment) &&
          (!filters.needsReview || c.review_count > 0),
      ),
    );
  }
  const params = new URLSearchParams();
  if (filters.moment) params.set("moment", filters.moment);
  if (filters.needsReview) params.set("needs_review", "true");
  const query = params.toString();
  return request<CustomerSummary[]>(`/customers${query ? `?${query}` : ""}`);
}

export async function getCustomer(id: number): Promise<CustomerDetail> {
  if (USE_MOCKS) return delay(mockDetail(id));
  return request<CustomerDetail>(`/customers/${id}`);
}

export async function injectSignal(id: number, signal: SignalCreate): Promise<CustomerDetail> {
  if (USE_MOCKS) {
    const current = mockDetail(id);
    if (id === 7 && /notary/i.test(signal.description)) {
      const after = clone(afterInjectFixture) as CustomerDetail;
      mock.details.set(id, after);
      syncSummary(after);
      return delay(after);
    }
    current.signals.unshift({
      id: Date.now(),
      date: signal.date ?? new Date().toISOString().slice(0, 10),
      kind: signal.kind,
      description: signal.description,
      amount: signal.amount ?? null,
      category: signal.kind === "transaction" ? "other" : null,
      recurring: false,
    });
    if (signal.amount) current.customer.balance += signal.amount;
    return delay(current);
  }
  return request<CustomerDetail>(`/customers/${id}/signals`, { method: "POST", body: signal });
}

export async function decideIntervention(
  interventionId: number,
  decision: "approve" | "dismiss",
): Promise<Intervention> {
  if (USE_MOCKS) {
    for (const detail of mock.details.values()) {
      const item = detail.interventions.find((i) => i.id === interventionId);
      if (item) {
        item.status = decision === "approve" ? "delivered" : "dismissed";
        syncSummary(detail);
        return delay(item);
      }
    }
    throw new ApiError(404, "Intervention not found");
  }
  return request<Intervention>(`/interventions/${interventionId}/decision`, {
    method: "POST",
    body: { decision },
  });
}

export async function getScale(): Promise<ScaleStats> {
  if (USE_MOCKS) return delay(scaleFixture as ScaleStats);
  return request<ScaleStats>("/scale");
}
