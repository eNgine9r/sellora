export type WorkspaceMembership = {
  workspace_id: string;
  workspace_name: string;
  workspace_slug: string;
  role: "OWNER" | "MANAGER" | "ANALYST";
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
