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
};

export type NovaPoshtaSettingsPayload = {
  api_key: string;
  sender_city_ref?: string | null;
  sender_warehouse_ref?: string | null;
  sender_counterparty_ref?: string | null;
  sender_contact_ref?: string | null;
  sender_phone?: string | null;
};

export type NovaPoshtaDirectoryItem = { ref: string; description: string; number?: string | null };
export type NovaPoshtaActionResponse = { success: boolean; message: string; tracking_number?: string | null; document_ref?: string | null; status?: string | null; errors?: string[] };
