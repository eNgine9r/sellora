import { apiRequest } from "@/services/api";
import { DirectConversation, DirectMessage } from "@/types/direct";

export function fetchDirectConversations() { return apiRequest<DirectConversation[]>("/direct/conversations"); }
export function fetchDirectMessages(conversationId: string) { return apiRequest<DirectMessage[]>(`/direct/conversations/${conversationId}/messages`); }
export function prepareDirectReply(conversationId: string, messageText: string) { return apiRequest(`/direct/conversations/${conversationId}/reply/prepare`, { method: "POST", body: JSON.stringify({ message_text: messageText }) }); }
export function sendDirectReply(conversationId: string, messageText: string, idempotencyKey: string) { return apiRequest(`/direct/conversations/${conversationId}/reply/send`, { method: "POST", headers: { "Idempotency-Key": idempotencyKey }, body: JSON.stringify({ message_text: messageText }) }); }
