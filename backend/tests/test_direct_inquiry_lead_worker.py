"""Regression coverage for inbound-only and bounded Direct lead sync."""
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.services import direct_inquiry_lead_worker as worker


@pytest.mark.parametrize(("message", "expected"), [
    ("Привіт! Яка ціна?", True),
    ("Хочу замовити годинник", True),
    ("Є у наявності?", True),
    ("беру", True),
    ("дякую", False),
    ("Добре", False),
    ("👍", False),
    ("https://shop.example/item", False),
    ("", False),
    ("  ", False),
    ("?", False),
])
def test_genuine_inquiry_filter(message, expected):
    assert worker.qualifies(message) is expected


def test_dry_run_does_not_write_or_create_lead(monkeypatch):
    class FakeDB:
        calls = 0
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def scalar(self, _stmt):
            return SimpleNamespace(id=uuid4())
        def scalars(self, _stmt):
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(all=lambda: [uuid4()])
            return SimpleNamespace(all=lambda: [
                SimpleNamespace(text="Хочу замовити", received_at=datetime.now(UTC))
            ])
        def commit(self):
            raise AssertionError("dry-run committed writes")
        def rollback(self):
            raise AssertionError("dry-run rolled back an unexpected transaction")
    monkeypatch.setattr(worker, "SessionLocal", FakeDB)
    monkeypatch.setattr(worker.DirectLeadService, "_ensure", lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("dry-run created a lead")
    ))
    assert worker.run_once(dry_run=True) == 0
