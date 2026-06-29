import { apiRequest } from "@/services/api";

export type FeedbackCategory = "ISSUE" | "IDEA" | "CONFUSION" | "PRAISE" | "OTHER";
export type FeedbackStatus = "NEW" | "REVIEWED" | "PLANNED" | "FIXED" | "WONT_FIX";

export type PilotFeedback = {
  id: string;
  category: FeedbackCategory;
  rating?: number | null;
  message: string;
  page_path?: string | null;
  status: FeedbackStatus;
  created_at: string;
  updated_at: string;
  user_id?: string | null;
};

export type PilotFeedbackCreate = {
  category: FeedbackCategory;
  rating?: number | null;
  message: string;
  page_path?: string | null;
};

function workspaceHeaders(workspaceId?: string): HeadersInit {
  return workspaceId ? { "X-Workspace-ID": workspaceId } : {};
}

export async function submitPilotFeedback(workspaceId: string, payload: PilotFeedbackCreate): Promise<PilotFeedback> {
  return apiRequest<PilotFeedback>("/feedback", { method: "POST", headers: workspaceHeaders(workspaceId), body: JSON.stringify(payload) });
}

export async function fetchPilotFeedback(workspaceId: string): Promise<PilotFeedback[]> {
  return apiRequest<PilotFeedback[]>("/feedback", { headers: workspaceHeaders(workspaceId) });
}

export async function updatePilotFeedbackStatus(workspaceId: string, feedbackId: string, status: FeedbackStatus): Promise<PilotFeedback> {
  return apiRequest<PilotFeedback>(`/feedback/${feedbackId}`, { method: "PATCH", headers: workspaceHeaders(workspaceId), body: JSON.stringify({ status }) });
}
