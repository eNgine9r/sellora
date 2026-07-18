import { apiRequest } from "@/services/api";
import { AISuggestion } from "@/types/ai";

export function fetchAISuggestions(conversationId: string) { return apiRequest<AISuggestion[]>(`/direct/conversations/${conversationId}/suggestions`); }
export function approveAISuggestion(suggestionId: string) { return apiRequest<AISuggestion>(`/ai/suggestions/${suggestionId}/approve`, { method: "POST" }); }
export function rejectAISuggestion(suggestionId: string, reason?: string) { return apiRequest<AISuggestion>(`/ai/suggestions/${suggestionId}/reject`, { method: "POST", body: JSON.stringify({ reason }) }); }
