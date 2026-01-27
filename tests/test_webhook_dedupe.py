from typing import Any

import pytest
from fastapi.testclient import TestClient


def test_webhook_dedupes_same_update_id(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"create": 0}

    def fake_create(
        content: str,
        parent_id: str,
        api_token: str,
        *,
        description: Any = None,
        client: Any = None,
    ) -> dict[str, Any]:
        calls["create"] += 1
        return {"id": "child-1"}

    monkeypatch.setattr("app.main.create_subtask", fake_create)
    from collections import OrderedDict

    monkeypatch.setattr("app.main._dedupe_store", OrderedDict())
    monkeypatch.setattr("app.main.time", type("T", (), {"time": staticmethod(lambda: 1000.0)}))

    payload = {
        "update_id": 99,
        "message": {
            "message_id": 12,
            "chat": {"id": 555, "type": "private"},
            "text": "hello",
        },
    }

    first = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json=payload,
    )
    second = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert calls["create"] == 1
    assert second.json()["data"]["duplicate"] is True
