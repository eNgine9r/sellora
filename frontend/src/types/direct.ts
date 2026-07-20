export type DirectConversationChannel = "SYNTHETIC" | "INSTAGRAM" | "MANUAL";
export type DirectMessageDirection = "INBOUND" | "OUTBOUND" | "INTERNAL";
export type ParticipantProfileStatus = "PENDING" | "READY" | "RETRY_PENDING" | "UNAVAILABLE";
export type InstagramHistorySyncStatus = "PENDING" | "RUNNING" | "COMPLETED" | "PARTIAL" | "RETRY_PENDING" | "FAILED_SAFE";

export type DirectConversation = {
  id: string;
  channel: DirectConversationChannel;
  participant_username?: string | null;
  participant_display_name?: string | null;
  participant_scoped_id?: string | null;
  participant_profile_picture_url?: string | null;
  participant_profile_picture_expires_at?: string | null;
  participant_follower_count?: number | null;
  participant_is_verified_user?: boolean | null;
  participant_is_user_follow_business?: boolean | null;
  participant_is_business_follow_user?: boolean | null;
  participant_profile_status?: ParticipantProfileStatus | null;
  participant_profile_last_synced_at?: string | null;
  participant_profile_next_retry_at?: string | null;
  participant_profile_error_code?: string | null;
  status: string;
  priority: string;
  unread_count: number;
  ai_processing_status: string;
  last_message_at?: string | null;
  messaging_window_expires_at?: string | null;
  provider_sync_status?: string | null;
};

export type DirectMessage = {
  id: string;
  conversation_id: string;
  direction: DirectMessageDirection;
  sender_type?: string;
  message_type?: string;
  text?: string | null;
  received_at: string;
  provider?: string | null;
  provider_message_id?: string | null;
  delivery_status?: string | null;
  message_payload_type?: string | null;
  seen_at?: string | null;
  edited_at?: string | null;
  edit_count?: number;
  reaction?: string | null;
  reaction_updated_at?: string | null;
};

export type DirectLiveEvent = {
  message_id: string;
  conversation_id: string;
  participant_display_name?: string | null;
  participant_username?: string | null;
  text_preview: string;
  received_at: string;
  unread_count: number;
  order_intent: boolean;
  order_intent_confidence: number;
  order_intent_reason?: string | null;
};

export type DirectLiveSummary = {
  server_time: string;
  unread_total: number;
  order_intent_count: number;
  events: DirectLiveEvent[];
};

export type InstagramHistorySync = {
  id: string;
  workspace_id: string;
  instagram_connection_id: string;
  status: InstagramHistorySyncStatus;
  conversation_limit: number;
  messages_per_conversation: number;
  conversation_pages_processed: number;
  conversations_discovered: number;
  conversations_synced: number;
  messages_discovered: number;
  messages_imported: number;
  messages_existing: number;
  messages_unavailable: number;
  error_count: number;
  rate_limit_count: number;
  attempt_count: number;
  last_error_code?: string | null;
  next_retry_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  last_synced_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type MessageOperation = {
  id: string;
  conversation_id: string;
  status: string;
  provider_message_id?: string | null;
  direct_message_id?: string | null;
  manual_reconciliation_required: boolean;
  blind_retry_blocked: boolean;
  last_error_code?: string | null;
};
