import json
from datetime import date

import httpx
import pytest

from app.todoist import TodoistServiceError, ensure_todo_later_task


def test_ensure_todo_later_task_returns_existing_task() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.url.path == "/rest/v2/tasks"
        return httpx.Response(
            200,
            json=[{"id": "42", "content": "todo later", "due": {"date": date.today().isoformat()}}],
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    task_id = ensure_todo_later_task("todo later", "test-token", client=client)

    assert task_id == "42"


def test_ensure_todo_later_task_creates_missing_task() -> None:
    calls: list[tuple[str, dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json=[])
        if request.method == "POST":
            body = json.loads(request.content.decode("utf-8"))
            calls.append((request.url.path, body))
            return httpx.Response(200, json={"id": "99", "content": body["content"]})
        return httpx.Response(405)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    task_id = ensure_todo_later_task("todo later", "test-token", client=client)

    assert task_id == "99"
    assert calls == [("/rest/v2/tasks", {"content": "todo later", "due_string": "every day"})]


def test_ensure_todo_later_task_updates_due_date() -> None:
    calls: list[tuple[str, dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(
                200,
                json=[{"id": "42", "content": "todo later", "due": {"date": "2099-01-01"}}],
            )
        if request.method == "POST":
            body = json.loads(request.content.decode("utf-8"))
            calls.append((request.url.path, body))
            return httpx.Response(200, json={})
        return httpx.Response(405)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    task_id = ensure_todo_later_task("todo later", "test-token", client=client)

    assert task_id == "42"
    assert calls == [("/rest/v2/tasks/42", {"due_string": "today"})]


def test_ensure_todo_later_task_rejects_missing_name() -> None:
    with pytest.raises(TodoistServiceError) as excinfo:
        ensure_todo_later_task(" ", "test-token")

    assert excinfo.value.user_message == "Todo later task name is required"
