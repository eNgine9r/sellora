export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type WorkspaceMembership = {
  workspace_id: string;
  workspace_name: string;
  workspace_slug: string;
  role: "OWNER" | "MANAGER" | "ANALYST";
  currency_code: "UAH" | "USD";
};

export type CurrentUser = {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  last_login_at: string | null;
  memberships: WorkspaceMembership[];
};
