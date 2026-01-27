import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.config import get_settings
from app.main import app


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-telegram-token")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "test-secret")
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", "[]")
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHAT_IDS", "[]")
    monkeypatch.setenv("TELEGRAM_WHITELIST_REPLY", "false")
    monkeypatch.setenv("TRANSCRIBE_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("TODOIST_API_TOKEN", "test-todoist-token")
    monkeypatch.setenv("TODO_LATER_TASK_NAME", "todo later")
    get_settings.cache_clear()
    return TestClient(app)


@pytest.fixture(autouse=True)
def _stub_todoist(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_ensure(task_name: str, api_token: str, *, client=None) -> str:
        return "parent-test"

    def fake_create(
        content: str,
        parent_id: str,
        api_token: str,
        *,
        description=None,
        client=None,
    ) -> dict:
        return {"id": "child-test"}

    monkeypatch.setattr("app.main.ensure_todo_later_task", fake_ensure)
    monkeypatch.setattr("app.main.create_subtask", fake_create)


@pytest.fixture(autouse=True)
def _stub_telegram(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_send(chat_id: int, text: str, api_token: str, *, client=None) -> None:
        return None

    monkeypatch.setattr("app.main.send_telegram_message", fake_send)
