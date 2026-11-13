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
  archived_at: string | null;
  subscription: Subscription;
};

export type PlatformWorkspaceDetail = PlatformWorkspace & {
  currency_code: string;
  timezone: string;
  active_member_count: number;
  archive_allowed: boolean;
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
  archived_workspaces?: number;
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
  archived: boolean;
};

export type PlatformUserSegment = "STANDARD" | "DEMO_ONLY" | "NO_ENABLED_WORKSPACE";

export type PlatformUserFilters = {
  search: string;
  segment: "" | PlatformUserSegment;
  active: "" | "true" | "false";
};

type PlatformUserSummary = {
  total_accounts: number;
  enabled_accounts: number;
  demo_only_accounts: number;
  accounts_without_enabled_workspace: number;
};

export type PlatformUser = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
  owned_workspace_count: number;
  segment: PlatformUserSegment;
};

type PlatformWorkspaceTeamPage = {
  items: {
    id: string;
    first_name: string;
    last_name: string;
    role: "MANAGER" | "ANALYST";
    is_active: boolean;
  }[];
  next_cursor: string | null;
};

type PlatformUserDetail = PlatformUser & {
  workspaces: (Pick<PlatformWorkspace, "id" | "name" | "slug" | "is_active" | "archived_at"> & {
    role: "OWNER" | "MANAGER" | "ANALYST";
  })[];
  next_cursor: string | null;
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
  workspaceTeam(id: string, cursor: string | null, signal: AbortSignal) {
    const query = cursor ? `?cursor=${encodeURIComponent(cursor)}` : "";
    return read<PlatformWorkspaceTeamPage>(`workspaces/${encodeURIComponent(id)}/team${query}`, signal);
  },
  userSummary: (signal: AbortSignal) => read<PlatformUserSummary>("users/summary", signal),
  users(filters: PlatformUserFilters, cursor: string | null, signal: AbortSignal) {
    return apiRequest<{ items: PlatformUser[]; next_cursor: string | null }>("/platform-admin/users/search", {
      method: "POST",
      signal,
      headers: proofHeaders(),
      cache: "no-store",
      body: JSON.stringify({
        q: filters.search || undefined,
        segment: filters.segment || undefined,
        active: filters.active ? filters.active === "true" : undefined,
        cursor: cursor || undefined,
      }),
    });
  },
  user(id: string, cursor: string | null, signal: AbortSignal) {
    const query = cursor ? `?cursor=${encodeURIComponent(cursor)}` : "";
    return read<PlatformUserDetail>(`users/${encodeURIComponent(id)}${query}`, signal);
  },
  setArchived(id: string, archived: boolean) {
    const action = archived ? "archive" : "restore";
    return apiRequest<void>(`/platform-admin/workspaces/${encodeURIComponent(id)}/${action}`, {
      method: "POST", headers: proofHeaders(), cache: "no-store",
    });
  },
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
        archived: filters.archived,
        cursor: cursor || undefined,
      }),
    });
  },
};
