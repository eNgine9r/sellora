export type InstagramConnectionStatus = "PENDING" | "CONNECTED" | "TOKEN_EXPIRED" | "PERMISSION_MISSING" | "WEBHOOK_INACTIVE" | "RECONNECT_REQUIRED" | "DISCONNECTED" | "FAILED";

export type InstagramConnectionStatusResponse = {
  workspace_id: string;
  status: InstagramConnectionStatus | "DISCONNECTED";
  instagram_username?: string | null;
  instagram_account_type?: string | null;
  granted_permissions: string[];
  subscribed_webhook_fields: string[];
  token_expires_at?: string | null;
  connected_at?: string | null;
  disconnected_at?: string | null;
  last_webhook_at?: string | null;
  last_message_received_at?: string | null;
  last_message_sent_at?: string | null;
  token_present: boolean;
  send_enabled: boolean;
  auto_send_enabled: boolean;
};

export type InstagramConnectResponse = { authorization_url: string; expires_at: string };
export type InstagramValidateResponse = { status: string; permission_ok: boolean; token_present: boolean };
export type InstagramDisconnectResponse = { status: string; disconnected: boolean };
