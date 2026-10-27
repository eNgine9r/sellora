export type MetaAdsStatus = {
  workspace_id: string; connection_status: string; connected: boolean;
  configured: boolean; can_connect: boolean; can_sync: boolean; sync_enabled: boolean;
  account_selection_required: boolean; blockers: string[];
  account_name: string | null; currency: string | null; timezone: string | null;
  last_synced_at: string | null; last_error_code: string | null;
};
export type MetaAdsAccount = { external_account_id: string; name: string; currency: string; timezone: string; selectable: boolean; reason: string | null };
export type MetaAdsAccounts = { accounts: MetaAdsAccount[]; selected_account_id: string | null; workspace_currency: string; workspace_timezone: string };
export type MetaAdsSync = { status: "SUCCEEDED"; metrics_created: number; metrics_updated: number; last_synced_at: string; reach_measure: "not_imported" };
