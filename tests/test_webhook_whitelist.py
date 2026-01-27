from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def _make_client(monkeypatch: pytest.MonkeyPatch, **env: str) -> TestClient:
    defaults = {
        "TELEGRAM_BOT_TOKEN": "test-telegram-token",
        "TELEGRAM_WEBHOOK_SECRET": "test-secret",
        "TODOIST_API_TOKEN": "test-todoist-token",
        "TODO_LATER_TASK_NAME": "todo later",
    }
    for key, value in defaults.items():
        monkeypatch.setenv(key, value)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    return TestClient(app)


def test_webhook_allows_whitelisted_user(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, int] = {"ensure": 0}

    def fake_ensure(task_name: str, api_token: str, *, client: Any = None) -> str:
        calls["ensure"] += 1
        return "parent-123"

    monkeypatch.setattr("app.main.ensure_todo_later_task", fake_ensure)

    client = _make_client(monkeypatch, TELEGRAM_ALLOWED_USER_IDS="50")
    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 20,
            "message": {
                "message_id": 21,
                "chat": {"id": 99, "type": "private"},
                "from": {"id": 50, "is_bot": False},
                "text": "hello",
            },
        },
    )

    assert response.status_code == 200
    assert calls["ensure"] == 1


def test_webhook_allows_whitelisted_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, int] = {"ensure": 0}

    def fake_ensure(task_name: str, api_token: str, *, client: Any = None) -> str:
        calls["ensure"] += 1
        return "parent-123"

    monkeypatch.setattr("app.main.ensure_todo_later_task", fake_ensure)

    client = _make_client(monkeypatch, TELEGRAM_ALLOWED_CHAT_IDS="99")
    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 21,
            "message": {
                "message_id": 22,
                "chat": {"id": 99, "type": "group"},
                "from": {"id": 51, "is_bot": False},
                "text": "hello",
            },
        },
    )

    assert response.status_code == 200
    assert calls["ensure"] == 1


def test_webhook_denies_unlisted_sender(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, int] = {"ensure": 0, "send": 0}

    def fake_ensure(task_name: str, api_token: str, *, client: Any = None) -> str:
        calls["ensure"] += 1
        return "parent-123"

    def fake_send(chat_id: int, text: str, api_token: str, *, client: Any = None) -> None:
        calls["send"] += 1

    monkeypatch.setattr("app.main.ensure_todo_later_task", fake_ensure)
    monkeypatch.setattr("app.main.send_telegram_message", fake_send)

    client = _make_client(
        monkeypatch,
        TELEGRAM_ALLOWED_USER_IDS="1",
        TELEGRAM_ALLOWED_CHAT_IDS="2",
    )
    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 22,
            "message": {
                "message_id": 23,
                "chat": {"id": 99, "type": "private"},
                "from": {"id": 50, "is_bot": False},
                "text": "hello",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert calls["ensure"] == 0
    assert calls["send"] == 0


def test_webhook_allows_channel_post_by_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, int] = {"ensure": 0}

    def fake_ensure(task_name: str, api_token: str, *, client: Any = None) -> str:
        calls["ensure"] += 1
        return "parent-123"

    monkeypatch.setattr("app.main.ensure_todo_later_task", fake_ensure)

    client = _make_client(monkeypatch, TELEGRAM_ALLOWED_CHAT_IDS="-100")
    response = client.post(
        "/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 23,
            "channel_post": {
                "message_id": 24,
                "chat": {"id": -100, "type": "channel"},
                "text": "hello",
            },
        },
    )

    assert response.status_code == 200
    assert calls["ensure"] == 1
