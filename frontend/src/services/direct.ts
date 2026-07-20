import { apiRequest } from "@/services/api";
import { DirectConversation, DirectMessage, InstagramHistorySync, MessageOperation } from "@/types/direct";

export function fetchDirectConversations() { return apiRequest<DirectConversation[]>("/direct/conversations"); }
export function fetchDirectMessages(conversationId: string) { return apiRequest<DirectMessage[]>(`/direct/conversations/${conversationId}/message-timeline`); }
export function refreshDirectParticipantProfile(conversationId: string) { return apiRequest<DirectConversation>(`/direct/conversations/${conversationId}/participant-profile/refresh`, { method: "POST" }); }
export function fetchInstagramHistorySync() { return apiRequest<InstagramHistorySync | null>("/direct/history-sync"); }
export function startInstagramHistorySync(conversationLimit = 100, messagesPerConversation = 20) {
  return apiRequest<InstagramHistorySync>("/direct/history-sync", {
    method: "POST",
    body: JSON.stringify({ conversation_limit: conversationLimit, messages_per_conversation: messagesPerConversation }),
  });
}
export function addSyntheticMessage(conversationId: string, text: string) { return apiRequest<DirectMessage>(`/direct/conversations/${conversationId}/messages`, { method: "POST", body: JSON.stringify({ text }) }); }
export function runDirectAnalysis(conversationId: string) { return apiRequest(`/direct/conversations/${conversationId}/analyze`, { method: "POST" }); }
export function prepareDirectReply(conversationId: string, messageText: string, humanAgentRequested = false) { return apiRequest<{ ready: boolean; blockers: string[]; warnings: string[]; message_preview: string }>(`/direct/conversations/${conversationId}/reply/prepare`, { method: "POST", body: JSON.stringify({ message_text: messageText, human_agent_requested: humanAgentRequested }) }); }
export function sendDirectReply(conversationId: string, messageText: string, idempotencyKey: string) { return apiRequest(`/direct/conversations/${conversationId}/reply/send`, { method: "POST", headers: { "Idempotency-Key": idempotencyKey }, body: JSON.stringify({ message_text: messageText }) }); }
export function fetchMessageOperation(operationId: string) { return apiRequest<MessageOperation>(`/direct/message-operations/${operationId}`); }
export function reconcileMessageOperation(operationId: string) { return apiRequest<MessageOperation>(`/direct/message-operations/${operationId}/reconcile`, { method: "POST" }); }