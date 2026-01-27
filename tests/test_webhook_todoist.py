from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.telegram_normalizer import FORWARDED_EMPTY_PROMPT, UNSUPPORTED_MESSAGE_PROMPT


def test_webhook_creates_todoist_subtask(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}
    messages: list[str] = []

    def fake_ensure(task_name: str, api_token: str, *, client: Any = None) -> str:
        calls["ensure"] = {"task_name": task_name, "api_token": api_token}
        return "parent-123"

    def fake_create(
        content: str,
        parent_id: str,
        api_token: str,
        *,
        description: Any = None,
        client: Any = None,
    ) -> dict[str, Any]:
        calls["create"] = {
            "content": content,
            "parent_id": parent_id,
            "api_token": api_token,
            "description": description,
        }
        return {"id": "child-1", "url": "https://todoist.com/showTask?id=child-1"}

    def fake_send(chat_id: int, text: str, api_token: str, *, client: Any = None) -> None:
        messages.append(text)

    monkeypatch.setattr("app.main.ensure_todo_later_task", fake_ensure)
    monkeypatch.setattr("app.main.create_subtask", fake_create)
    monkeypatch.setattr("app.main.send_telegram_message", fake_send)

    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 10,
            "message": {
                "message_id": 12,
                "chat": {"id": 555, "type": "private"},
                "text": "hello",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["normalized_text"] == "hello"
    assert calls["ensure"]["task_name"] == "todo later"
    assert calls["create"]["content"] == "hello"
    assert "update_id=10" in calls["create"]["description"]
    assert "message_id=12" in calls["create"]["description"]
    assert len(messages) == 1
    assert "https://todoist.com/showTask?id=child-1" in messages[0]
    assert calls["create"]["parent_id"] == "parent-123"


@pytest.mark.parametrize("prompt", [UNSUPPORTED_MESSAGE_PROMPT, FORWARDED_EMPTY_PROMPT])
def test_webhook_creates_subtask_for_unsupported_message(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    prompt: str,
) -> None:
    def fake_ensure(task_name: str, api_token: str, *, client: Any = None) -> str:
        return "parent-123"

    captured: dict[str, Any] = {}
    messages: list[str] = []

    def fake_create(
        content: str,
        parent_id: str,
        api_token: str,
        *,
        description: Any = None,
        client: Any = None,
    ) -> dict[str, Any]:
        captured["content"] = content
        captured["description"] = description
        return {"id": "child-2"}

    def fake_send(chat_id: int, text: str, api_token: str, *, client: Any = None) -> None:
        messages.append(text)

    monkeypatch.setattr("app.main.ensure_todo_later_task", fake_ensure)
    monkeypatch.setattr("app.main.create_subtask", fake_create)
    monkeypatch.setattr("app.main.normalize_update", lambda _: prompt)
    monkeypatch.setattr("app.main.send_telegram_message", fake_send)

    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 11,
            "message": {"message_id": 99, "chat": {"id": 555, "type": "private"}},
        },
    )

    assert response.status_code == 200
    assert "unsupported" in captured["content"].lower()
    assert prompt in captured["content"]
    assert "update_id=11" in captured["description"]
    assert len(messages) == 1


def test_webhook_sends_failure_message(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []

    def fake_ensure(task_name: str, api_token: str, *, client: Any = None) -> str:
        return "parent-123"

    def fake_create(*_: Any, **__: Any) -> dict[str, Any]:
        raise Exception("boom")

    def fake_send(chat_id: int, text: str, api_token: str, *, client: Any = None) -> None:
        messages.append(text)

    monkeypatch.setattr("app.main.ensure_todo_later_task", fake_ensure)
    monkeypatch.setattr("app.main.create_subtask", fake_create)
    monkeypatch.setattr("app.main.send_telegram_message", fake_send)

    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 12,
            "message": {"message_id": 77, "chat": {"id": 555, "type": "private"}},
        },
    )

    assert response.status_code == 500
    assert len(messages) == 1
    assert messages[0].startswith("创建失败")
