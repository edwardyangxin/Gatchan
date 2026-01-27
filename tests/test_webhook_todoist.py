from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.telegram_normalizer import (
    DOCUMENT_ONLY_PROMPT,
    FORWARDED_EMPTY_PROMPT,
    IMAGE_ONLY_PROMPT,
    UNSUPPORTED_MESSAGE_PROMPT,
)


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


def test_webhook_photo_creates_task_with_image_url(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_get(file_id: str, api_token: str, *, client: Any = None) -> str:
        captured["file_id"] = file_id
        return "https://files.example.com/photo.jpg"

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
        return {"id": "child-photo"}

    monkeypatch.setattr("app.main.get_telegram_file_url", fake_get)
    monkeypatch.setattr("app.main.create_subtask", fake_create)

    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 20,
            "message": {
                "message_id": 100,
                "chat": {"id": 555, "type": "private"},
                "caption": "photo note",
                "photo": [
                    {"file_id": "small", "width": 90, "height": 90},
                    {"file_id": "large", "width": 320, "height": 320},
                ],
            },
        },
    )

    assert response.status_code == 200
    assert captured["content"] == "photo note"
    assert captured["file_id"] == "large"
    assert "image_url=https://files.example.com/photo.jpg" in captured["description"]


def test_webhook_photo_without_caption_uses_default_title(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_get(file_id: str, api_token: str, *, client: Any = None) -> str:
        return "https://files.example.com/photo.jpg"

    def fake_create(
        content: str,
        parent_id: str,
        api_token: str,
        *,
        description: Any = None,
        client: Any = None,
    ) -> dict[str, Any]:
        captured["content"] = content
        return {"id": "child-photo"}

    monkeypatch.setattr("app.main.get_telegram_file_url", fake_get)
    monkeypatch.setattr("app.main.create_subtask", fake_create)

    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 21,
            "message": {
                "message_id": 101,
                "chat": {"id": 555, "type": "private"},
                "photo": [
                    {"file_id": "only", "width": 320, "height": 320},
                ],
            },
        },
    )

    assert response.status_code == 200
    assert captured["content"] == IMAGE_ONLY_PROMPT


def test_webhook_photo_getfile_failure_still_creates_task(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_get(*_: Any, **__: Any) -> str:
        raise ValueError("boom")

    def fake_create(
        content: str,
        parent_id: str,
        api_token: str,
        *,
        description: Any = None,
        client: Any = None,
    ) -> dict[str, Any]:
        captured["description"] = description
        return {"id": "child-photo"}

    monkeypatch.setattr("app.main.get_telegram_file_url", fake_get)
    monkeypatch.setattr("app.main.create_subtask", fake_create)

    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 22,
            "message": {
                "message_id": 102,
                "chat": {"id": 555, "type": "private"},
                "caption": "photo note",
                "photo": [
                    {"file_id": "only", "width": 320, "height": 320},
                ],
            },
        },
    )

    assert response.status_code == 200
    assert "image_url=" not in captured["description"]


def test_webhook_document_creates_task_with_file_url(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_get(file_id: str, api_token: str, *, client: Any = None) -> str:
        captured["file_id"] = file_id
        return "https://files.example.com/file.pdf"

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
        return {"id": "child-doc"}

    monkeypatch.setattr("app.main.get_telegram_file_url", fake_get)
    monkeypatch.setattr("app.main.create_subtask", fake_create)

    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 30,
            "message": {
                "message_id": 300,
                "chat": {"id": 555, "type": "private"},
                "caption": "pdf note",
                "document": {"file_id": "doc-1", "file_name": "note.pdf"},
            },
        },
    )

    assert response.status_code == 200
    assert captured["content"] == "pdf note"
    assert captured["file_id"] == "doc-1"
    assert "file_url=https://files.example.com/file.pdf" in captured["description"]


def test_webhook_document_without_caption_uses_filename(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_get(file_id: str, api_token: str, *, client: Any = None) -> str:
        return "https://files.example.com/file.pdf"

    def fake_create(
        content: str,
        parent_id: str,
        api_token: str,
        *,
        description: Any = None,
        client: Any = None,
    ) -> dict[str, Any]:
        captured["content"] = content
        return {"id": "child-doc"}

    monkeypatch.setattr("app.main.get_telegram_file_url", fake_get)
    monkeypatch.setattr("app.main.create_subtask", fake_create)

    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 31,
            "message": {
                "message_id": 301,
                "chat": {"id": 555, "type": "private"},
                "document": {"file_id": "doc-2", "file_name": "note.pdf"},
            },
        },
    )

    assert response.status_code == 200
    assert captured["content"] == "File from Telegram: note.pdf"


def test_webhook_document_uses_default_prompt_without_filename(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_get(file_id: str, api_token: str, *, client: Any = None) -> str:
        return "https://files.example.com/file.pdf"

    def fake_create(
        content: str,
        parent_id: str,
        api_token: str,
        *,
        description: Any = None,
        client: Any = None,
    ) -> dict[str, Any]:
        captured["content"] = content
        return {"id": "child-doc"}

    monkeypatch.setattr("app.main.get_telegram_file_url", fake_get)
    monkeypatch.setattr("app.main.create_subtask", fake_create)

    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 32,
            "message": {
                "message_id": 302,
                "chat": {"id": 555, "type": "private"},
                "document": {"file_id": "doc-3"},
            },
        },
    )

    assert response.status_code == 200
    assert captured["content"] == DOCUMENT_ONLY_PROMPT
