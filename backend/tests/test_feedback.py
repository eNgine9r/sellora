from uuid import uuid4

from pydantic import ValidationError

from app.models.pilot_feedback import PilotFeedback, PilotFeedbackStatus
from app.schemas.feedback import PilotFeedbackCreate, PilotFeedbackUpdate
from app.services.feedback_service import PilotFeedbackService


class FakeDb:
    def __init__(self) -> None:
        self.added = []
        self.committed = False

    def add(self, model) -> None:
        self.added.append(model)

    def flush(self) -> None:
        pass

    def commit(self) -> None:
        self.committed = True

    def refresh(self, model) -> None:
        pass


def test_feedback_create_requires_message_and_valid_category() -> None:
    payload = PilotFeedbackCreate.model_validate({"category": "ISSUE", "rating": 5, "message": "Import dry-run was clear", "page_path": "/settings/import"})

    assert payload.category.value == "ISSUE"
    assert payload.rating == 5

    try:
        PilotFeedbackCreate.model_validate({"category": "BROKEN", "message": "ok"})
    except ValidationError as exc:
        assert any(error["loc"] == ("category",) for error in exc.errors())
    else:
        raise AssertionError("Invalid feedback category should be rejected")

    try:
        PilotFeedbackCreate.model_validate({"category": "ISSUE", "message": ""})
    except ValidationError as exc:
        assert any(error["loc"] == ("message",) for error in exc.errors())
    else:
        raise AssertionError("Empty feedback message should be rejected")


def test_feedback_service_submits_workspace_scoped_record_without_secret_payload() -> None:
    db = FakeDb()
    service = PilotFeedbackService(db)  # type: ignore[arg-type]
    workspace_id = uuid4()
    user_id = uuid4()

    record = service.submit(workspace_id, PilotFeedbackCreate(category="CONFUSION", message="I did not understand import warnings", page_path="/settings/import"), user_id, "Synthetic Browser")

    assert isinstance(record, PilotFeedback)
    assert record.workspace_id == workspace_id
    assert record.user_id == user_id
    assert record.category == "CONFUSION"
    assert record.status == PilotFeedbackStatus.NEW.value
    assert record.user_agent == "Synthetic Browser"
    assert db.committed
    assert any(getattr(item, "entity_type", None) == "PilotFeedback" for item in db.added)


def test_feedback_update_status_schema_uses_english_constants() -> None:
    payload = PilotFeedbackUpdate.model_validate({"status": "PLANNED"})

    assert payload.status.value == "PLANNED"
