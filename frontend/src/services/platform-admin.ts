import { apiRequest } from "@/services/api";

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

type ProductUsageReport = {
  days: UsageDays;
  from_day: string;
  to_day: string;
  as_of: string;
  coverage_from: string | null;
  coverage: "complete" | "partial" | "unavailable";
  dropped_operations: number | null;
  totals: ProductUsageTotals | null;
};

export type WorkspaceFilters = {
  search: string;
  active: "" | "true" | "false";
  demo: "" | "true" | "false";
};

function read<T>(path: string, signal: AbortSignal) {
  return apiRequest<T>(`/platform-admin/${path}`, { signal, cache: "no-store" });
}

export const platformAdminApi = {
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
      cache: "no-store",
      body: JSON.stringify({
        limit: 20,
        q: filters.search || undefined,
        active: filters.active ? filters.active === "true" : undefined,
        demo: filters.demo ? filters.demo === "true" : undefined,
        cursor: cursor || undefined,
      }),
    });
  },
};
