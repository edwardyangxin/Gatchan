import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.todoist import TodoistServiceError, cleanup_completed_subtasks


def _make_client(handler):
    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport)


def test_cleanup_completed_subtasks_deletes_old_items() -> None:
    now = datetime(2026, 1, 27, tzinfo=timezone.utc)
    cutoff = now - timedelta(days=7)
    old = (cutoff - timedelta(hours=1)).isoformat()
    recent = (cutoff + timedelta(hours=1)).isoformat()

    calls = {"sync": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/archive/items"):
            items = [
                {"id": 1, "completed_at": old},
                {"id": 2, "completed_at": recent},
            ]
            return httpx.Response(200, json=items)
        if request.url.path.endswith("/sync"):
            calls["sync"] += 1
            payload = json.loads(request.content.decode("utf-8"))
            assert payload["commands"][0]["type"] == "item_delete"
            assert payload["commands"][0]["args"]["id"] == 1
            return httpx.Response(200, json={"sync_status": {}})
        raise AssertionError("unexpected request")

    client = _make_client(handler)

    deleted = cleanup_completed_subtasks(
        "parent-1",
        "token",
        client=client,
        now=now,
        max_delete=10,
    )

    assert deleted == 1
    assert calls["sync"] == 1


def test_cleanup_completed_subtasks_skips_recent_items() -> None:
    now = datetime(2026, 1, 27, tzinfo=timezone.utc)
    recent = (now - timedelta(days=1)).isoformat()

    calls = {"sync": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/archive/items"):
            return httpx.Response(200, json=[{"id": 2, "completed_at": recent}])
        if request.url.path.endswith("/sync"):
            calls["sync"] += 1
            return httpx.Response(200, json={"sync_status": {}})
        raise AssertionError("unexpected request")

    client = _make_client(handler)

    deleted = cleanup_completed_subtasks(
        "parent-1",
        "token",
        client=client,
        now=now,
    )

    assert deleted == 0
    assert calls["sync"] == 0


def test_cleanup_completed_subtasks_raises_on_archive_failure() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = _make_client(handler)

    with pytest.raises(TodoistServiceError):
        cleanup_completed_subtasks("parent-1", "token", client=client)
