export type IntegrationStatus = "DISCONNECTED" | "CONNECTED" | "ERROR";

export type NovaPoshtaSettings = {
  provider: "NOVA_POSHTA";
  status: IntegrationStatus;
  connection_name: string | null;
  connected_at: string | null;
  last_sync_at: string | null;
  masked_api_key: string | null;
  sender_city_ref: string | null;
  sender_warehouse_ref: string | null;
  sender_counterparty_ref: string | null;
  sender_contact_ref: string | null;
  sender_phone: string | null;
  provider_writes_enabled: boolean;
  sender_configured: boolean;
};

export type NovaPoshtaSettingsPayload = {
  api_key?: string | null;
  sender_city_ref?: string | null;
  sender_warehouse_ref?: string | null;
  sender_counterparty_ref?: string | null;
  sender_contact_ref?: string | null;
  sender_phone?: string | null;
};

export type NovaPoshtaDirectoryItem = { ref: string; description: string; number?: string | null };
export type NovaPoshtaActionResponse = {
  success: boolean;
  message: string;
  tracking_number?: string | null;
  document_ref?: string | null;
  status?: string | null;
  raw_status?: string | null;
  normalized_status?: string | null;
  operation_state?: string | null;
  reused_existing_result?: boolean;
  reconciliation_attempted?: boolean;
  manual_reconciliation_required?: boolean;
  manual_review_required?: boolean;
  blind_retry_blocked?: boolean;
  errors?: string[];
};
