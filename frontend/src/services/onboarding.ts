import { apiRequest } from "@/services/api";

function workspaceHeaders(workspaceId?: string): HeadersInit {
  return workspaceId ? { "X-Workspace-ID": workspaceId } : {};
}

export type OnboardingStepKey = "workspace_configured" | "product_created" | "stock_added" | "lead_or_customer_created" | "order_created";
export type OnboardingNextAction = "CONFIGURE_WORKSPACE" | "ADD_PRODUCT" | "ADD_STOCK" | "ADD_LEAD_OR_CUSTOMER" | "CREATE_ORDER" | "EXPLORE_DASHBOARD";

export type OnboardingStatus = {
  workspace_id: string;
  role: "OWNER" | "MANAGER" | "ANALYST";
  is_demo_workspace: boolean;
  is_empty: boolean;
  progress_percent: number;
  completed_steps: number;
  total_steps: number;
  steps: Record<OnboardingStepKey, boolean>;
  suggested_next_action: OnboardingNextAction;
};

export async function fetchOnboardingStatus(workspaceId: string): Promise<OnboardingStatus> {
  return apiRequest<OnboardingStatus>("/onboarding/status", { headers: workspaceHeaders(workspaceId) });
}
