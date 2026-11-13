import { ApiError, apiRequest } from "@/services/api";

export type PlatformRole = "PLATFORM_ADMIN" | "PLATFORM_SUPPORT" | "PLATFORM_AUDITOR";
export type SubscriptionStatus = "UNMANAGED" | "PENDING" | "TRIALING" | "ACTIVE" | "PAST_DUE" | "CANCELED" | "EXPIRED";

type PlatformIdentity = {
  operator_id: string;
  role: PlatformRole;
  capabilities: string[];
};

type Subscription = {
  status: SubscriptionStatus;
  plan_code: string | null;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
};

export type PlatformWorkspace = {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  is_demo: boolean;
  created_at: string;
  subscription: Subscription;
};

export type PlatformWorkspaceDetail = PlatformWorkspace & {
  currency_code: string;
  timezone: string;
  active_member_count: number;
};

type WorkspacePage = {
  items: PlatformWorkspace[];
  next_cursor: string | null;
  as_of: string;
};

type PlatformSummary = {
  as_of: string;
  total_workspaces: number;
  enabled_workspaces: number;
  demo_workspaces: number;
  workspaces_with_current_term: number;
};

export type UsageDays = 7 | 30;

type ProductUsageTotals = {
  active_workspaces: number;
  active_workspace_days: number;
  activated_workspaces: number;
  first_products: number;
  first_orders: number;
  orders_created: number;
  integration_days: number;
};

export type ProductUsageDay = {
  day: string;
  orders_created: number;
  dropped_operations: number;
};

type ProductUsageReport = {
  days: UsageDays;
  from_day: string;
  to_day: string;
  as_of: string;
  coverage_from: string | null;
  coverage: "complete" | "partial" | "unavailable";
  dropped_operations: number | null;
  totals: ProductUsageTotals | null;
  daily?: ProductUsageDay[];
};

export type WorkspaceFilters = {
  search: string;
  active: "" | "true" | "false";
  demo: "" | "true" | "false";
  subscriptionStatus: "" | SubscriptionStatus;
};

let mfaProof: string | undefined;

export function clearPlatformMfaProof() {
  mfaProof = undefined;
}

export function platformMfaError(error: unknown): string | undefined {
  if (!(error instanceof ApiError) || !error.detail || typeof error.detail !== "object") return;
  const detail = (error.detail as { detail?: unknown }).detail;
  return typeof detail === "string" ? detail : undefined;
}

function proofHeaders(): HeadersInit {
  return mfaProof ? { "X-Sellora-Platform-MFA": mfaProof } : {};
}

function read<T>(path: string, signal: AbortSignal) {
  return apiRequest<T>(`/platform-admin/${path}`, { signal, headers: proofHeaders(), cache: "no-store" });
}

export const platformAdminApi = {
  async verifyMfa(code: string) {
    const result = await apiRequest<{ proof: string }>("/platform-admin/mfa/verify", {
      method: "POST",
      cache: "no-store",
      body: JSON.stringify({ code }),
    });
    mfaProof = result.proof;
  },
  identity: (signal: AbortSignal) => read<PlatformIdentity>("me", signal),
  summary: (signal: AbortSignal) => read<PlatformSummary>("summary", signal),
  activity(days: UsageDays, workspaceId: string | undefined, signal: AbortSignal) {
    const path = workspaceId ? `workspaces/${encodeURIComponent(workspaceId)}/activity` : "activity/summary";
    return read<ProductUsageReport>(`${path}?days=${days}`, signal);
  },
  detail: (id: string, signal: AbortSignal) => read<PlatformWorkspaceDetail>(`workspaces/${encodeURIComponent(id)}`, signal),
  workspaces(filters: WorkspaceFilters, cursor: string | null, signal: AbortSignal) {
    return apiRequest<WorkspacePage>("/platform-admin/workspaces/search", {
      method: "POST",
      signal,
      headers: proofHeaders(),
      cache: "no-store",
      body: JSON.stringify({
        limit: 20,
        q: filters.search || undefined,
        active: filters.active ? filters.active === "true" : undefined,
        demo: filters.demo ? filters.demo === "true" : undefined,
        subscription_status: filters.subscriptionStatus || undefined,
        cursor: cursor || undefined,
      }),
    });
  },
};
