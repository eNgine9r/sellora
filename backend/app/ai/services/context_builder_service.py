from uuid import UUID
from app.repositories.ai_direct_repository import DirectMessageRepository

class AIContextBuilderService:
    def __init__(self, messages: DirectMessageRepository) -> None: self.messages = messages
    def build(self, workspace_id: UUID, conversation_id: UUID, max_messages: int = 20, max_input_characters: int = 12000) -> dict:
        items = self.messages.list_for_conversation(workspace_id, conversation_id)[-max_messages:]
        payload=[]; total=0
        for msg in items:
            text=(msg.text or '')[:max_input_characters]
            if total + len(text) > max_input_characters: break
            payload.append({'direction': msg.direction, 'sender_type': msg.sender_type, 'message_type': msg.message_type, 'text': text})
            total += len(text)
        return {'messages': payload, 'strategy': 'latest_messages_truncated_to_limit', 'input_characters': total}
