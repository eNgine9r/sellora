export type DirectConversationChannel = "SYNTHETIC" | "INSTAGRAM" | "MANUAL";
export type DirectMessageDirection = "INBOUND" | "OUTBOUND" | "INTERNAL";
export type DirectConversation = { id: string; channel: DirectConversationChannel; participant_username?: string | null; participant_display_name?: string | null; status: string; priority: string; unread_count: number; ai_processing_status: string; last_message_at?: string | null };
export type DirectMessage = { id: string; conversation_id: string; direction: DirectMessageDirection; text?: string | null; received_at: string; provider?: string | null; delivery_status?: string | null };
