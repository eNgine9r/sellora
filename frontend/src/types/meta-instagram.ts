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
  webhook_active: boolean;
  confirmed_webhook_fields: string[];
  missing_webhook_fields: string[];
  callback_configured: boolean;
  verify_token_configured: boolean;
  account_subscription_active: boolean;
  required_fields_confirmed: boolean;
  webhook_processing_enabled: boolean;
  last_error_code?: string | null;
  last_error_message?: string | null;
};

export type InstagramConnectResponse = { authorization_url: string; expires_at: string };
export type InstagramValidateResponse = { status: string; permission_ok: boolean; token_present: boolean };
export type InstagramDisconnectResponse = { status: string; disconnected: boolean };
