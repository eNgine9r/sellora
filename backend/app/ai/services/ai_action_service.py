from datetime import UTC, datetime
from uuid import UUID
from app.ai.exceptions import AIError
from app.models.ai_direct import AISuggestionStatus
from app.repositories.ai_direct_repository import AIRepository

class AIActionService:
    def __init__(self, repo: AIRepository) -> None: self.repo=repo
    def approve_suggestion(self, workspace_id: UUID, suggestion_id: UUID, user_id: UUID):
        s=self.repo.get_suggestion(workspace_id, suggestion_id)
        if not s: raise AIError('Suggestion not found','AI_SUGGESTION_NOT_FOUND')
        s.status=AISuggestionStatus.APPROVED.value; s.reviewed_by=user_id; s.reviewed_at=datetime.now(UTC); return s
    def reject_suggestion(self, workspace_id: UUID, suggestion_id: UUID, user_id: UUID, reason: str | None):
        s=self.repo.get_suggestion(workspace_id, suggestion_id)
        if not s: raise AIError('Suggestion not found','AI_SUGGESTION_NOT_FOUND')
        s.status=AISuggestionStatus.REJECTED.value; s.reviewed_by=user_id; s.reviewed_at=datetime.now(UTC); s.rejection_reason=reason; return s
    def apply_action(self, workspace_id: UUID, draft_id: UUID, idempotency_key: str):
        d=self.repo.get_action_draft(workspace_id, draft_id)
        if not d: raise AIError('Action draft not found','AI_ANALYSIS_NOT_FOUND')
        if d.status == AISuggestionStatus.APPLIED.value: return d
        if d.status != AISuggestionStatus.APPROVED.value: raise AIError('Action is not approved','AI_ACTION_NOT_APPROVED')
        if d.idempotency_key != idempotency_key: raise AIError('Idempotency key reused','AI_IDEMPOTENCY_KEY_REUSED')
        d.status=AISuggestionStatus.APPLIED.value; d.applied_at=datetime.now(UTC); return d
