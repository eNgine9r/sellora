from app.integrations.meta_instagram import runtime_worker


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class SuccessfulProcessor:
    def __init__(self, db) -> None:
        self.db = db

    def process_batch(self) -> int:
        return 2


class FailingProcessor:
    def __init__(self, db) -> None:
        self.db = db

    def process_batch(self) -> int:
        raise RuntimeError("batch failed")


def test_runtime_worker_disabled_by_default(monkeypatch):
    monkeypatch.delenv("META_INSTAGRAM_WEBHOOK_WORKER_ENABLED", raising=False)
    assert runtime_worker.webhook_worker_enabled() is False


def test_runtime_worker_enabled_from_environment(monkeypatch):
    monkeypatch.setenv("META_INSTAGRAM_WEBHOOK_WORKER_ENABLED", "true")
    assert runtime_worker.webhook_worker_enabled() is True


def test_process_batch_commits(monkeypatch):
    session = FakeSession()
    monkeypatch.setattr(runtime_worker, "SessionLocal", lambda: session)
    monkeypatch.setattr(runtime_worker, "InstagramWebhookProcessorService", SuccessfulProcessor)

    assert runtime_worker.process_webhook_batch() == 2
    assert session.committed is True
    assert session.rolled_back is False


def test_process_batch_rolls_back(monkeypatch):
    session = FakeSession()
    monkeypatch.setattr(runtime_worker, "SessionLocal", lambda: session)
    monkeypatch.setattr(runtime_worker, "InstagramWebhookProcessorService", FailingProcessor)

    try:
        runtime_worker.process_webhook_batch()
    except RuntimeError as exc:
        assert str(exc) == "batch failed"
    else:
        raise AssertionError("RuntimeError was not raised")

    assert session.committed is False
    assert session.rolled_back is True
