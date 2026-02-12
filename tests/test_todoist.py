import json

import httpx
import pytest

from app.todoist import TodoistServiceError, create_subtask


def test_create_subtask_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token"
        body = json.loads(request.content.decode("utf-8"))
        assert body == {"content": "hello", "parent_id": "123", "description": "meta here"}
        return httpx.Response(200, json={"id": "1", "content": "hello", "parent_id": "123"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    result = create_subtask("hello", "123", "test-token", description="meta here", client=client)

    assert result["id"] == "1"
    assert result["content"] == "hello"
    assert result["parent_id"] == "123"


def test_create_subtask_rejects_empty_content() -> None:
    with pytest.raises(TodoistServiceError) as excinfo:
        create_subtask("   ", "123", "test-token")

    assert excinfo.value.user_message == "Message text is required"


def test_create_subtask_handles_todoist_failure() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    with pytest.raises(TodoistServiceError) as excinfo:
        create_subtask("hello", "123", "test-token", client=client)

    assert excinfo.value.user_message == "Todoist request failed"


def test_create_subtask_handles_invalid_response() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "payload"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    with pytest.raises(TodoistServiceError) as excinfo:
        create_subtask("hello", "123", "test-token", client=client)

    assert excinfo.value.user_message == "Todoist response invalid"


def test_create_subtask_truncates_oversized_content() -> None:
    oversized_content = "x" * 800

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert len(body["content"]) == 500
        assert body["content"].endswith("...")
        return httpx.Response(200, json={"id": "1", "content": body["content"], "parent_id": "123"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    result = create_subtask(oversized_content, "123", "test-token", client=client)

    assert result["id"] == "1"
