export type AISuggestionStatus = "DRAFT" | "REVIEW_REQUIRED" | "APPROVED" | "REJECTED" | "APPLIED" | "FAILED" | "EXPIRED";
export type AISuggestion = { id: string; conversation_id: string; suggestion_type: string; status: AISuggestionStatus; title: string; draft_text?: string | null; summary?: string | null; confidence?: number | null };
